"""Telegram OTP kanali testlari."""
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from telegrambot.models import TelegramLink
from telegrambot import delivery


@override_settings(TELEGRAM_OTP_ENABLED=True, TELEGRAM_BOT_TOKEN='test-token')
class TelegramDeliveryTests(TestCase):

    def test_no_link_falls_back(self):
        """Raqam ulanmagan bo'lsa — Telegram yuborilmaydi (SMS'ga qaytiladi)."""
        self.assertFalse(delivery.try_send_telegram('+998900000011', '123456'))

    @patch('telegrambot.delivery.send_message', return_value=True)
    def test_linked_sends_via_telegram(self, mock_send):
        TelegramLink.objects.create(phone='998900000011', chat_id=555)
        # Turli formatdagi telefon ham topilishi kerak (normalizatsiya).
        self.assertTrue(delivery.try_send_telegram('+998 90 000 00 11', '123456'))
        mock_send.assert_called_once()
        self.assertEqual(mock_send.call_args[0][0], 555)  # chat_id
        self.assertIn('123456', mock_send.call_args[0][1])  # kod matnda

    @patch('telegrambot.delivery.send_message', return_value=False)
    def test_send_failure_returns_false(self, mock_send):
        TelegramLink.objects.create(phone='998900000011', chat_id=555)
        self.assertFalse(delivery.try_send_telegram('998900000011', '123456'))

    @override_settings(TELEGRAM_OTP_ENABLED=False)
    def test_disabled_never_sends(self):
        TelegramLink.objects.create(phone='998900000011', chat_id=555)
        self.assertFalse(delivery.try_send_telegram('998900000011', '123456'))


class LinkDemoCommandTests(TestCase):

    def test_link_command_creates_link(self):
        call_command('link_telegram_demo', '--phone=+998900000011', '--chat-id=999')
        link = TelegramLink.objects.get(phone='998900000011')
        self.assertEqual(link.chat_id, 999)

    def test_link_command_idempotent_update(self):
        call_command('link_telegram_demo', '--phone=+998900000011', '--chat-id=999')
        call_command('link_telegram_demo', '--phone=998900000011', '--chat-id=1000')
        self.assertEqual(TelegramLink.objects.filter(phone='998900000011').count(), 1)
        self.assertEqual(TelegramLink.objects.get(phone='998900000011').chat_id, 1000)


@override_settings(TELEGRAM_OTP_ENABLED=True, TELEGRAM_BOT_TOKEN='test-token')
class BotContactHandlerTests(TestCase):
    """/start va contact xabarini qayta ishlash (tarmoqsiz — send_message mock)."""

    @patch('telegrambot.bot.send_message', return_value=True)
    def test_contact_creates_link(self, _mock):
        from telegrambot.bot import handle_update
        update = {
            'update_id': 1,
            'message': {
                'chat': {'id': 777}, 'from': {'id': 777, 'username': 'aziz'},
                'contact': {'phone_number': '+998900000011', 'user_id': 777},
            },
        }
        handle_update(update)
        self.assertTrue(TelegramLink.objects.filter(phone='998900000011', chat_id=777).exists())

    @patch('telegrambot.bot.send_message', return_value=True)
    def test_foreign_contact_rejected(self, _mock):
        from telegrambot.bot import handle_update
        update = {
            'update_id': 2,
            'message': {
                'chat': {'id': 777}, 'from': {'id': 777},
                'contact': {'phone_number': '+998900000099', 'user_id': 888},  # boshqaning
            },
        }
        handle_update(update)
        self.assertFalse(TelegramLink.objects.filter(phone='998900000099').exists())
