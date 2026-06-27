"""SMS shlyuzi testlari — normalize, console, eskiz (mock), OTP integratsiya."""
from unittest.mock import patch, MagicMock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from sms.backends import normalize_phone, send_sms
from main.models import User, OTPCode


class NormalizePhoneTests(TestCase):
    def test_plus_prefix(self):
        self.assertEqual(normalize_phone('+998901234567'), '998901234567')

    def test_spaces_and_dashes(self):
        self.assertEqual(normalize_phone('+998 90 123-45-67'), '998901234567')

    def test_nine_digits(self):
        self.assertEqual(normalize_phone('901234567'), '998901234567')


@override_settings(SMS_BACKEND='console')
class ConsoleBackendTests(TestCase):
    def test_console_always_true(self):
        self.assertTrue(send_sms('+998901234567', 'Test'))


@override_settings(
    SMS_BACKEND='eskiz', SMS_ESKIZ_EMAIL='a@b.uz', SMS_ESKIZ_PASSWORD='x')
class EskizBackendTests(TestCase):
    def setUp(self):
        cache.delete('eskiz_token')

    @patch('sms.backends.requests.post')
    def test_login_then_send(self, mock_post):
        login_resp = MagicMock(status_code=200)
        login_resp.json.return_value = {'data': {'token': 'TKN'}}
        send_resp = MagicMock(status_code=200)
        mock_post.side_effect = [login_resp, send_resp]

        ok = send_sms('+998901234567', 'Kod: 123456')
        self.assertTrue(ok)
        self.assertEqual(mock_post.call_count, 2)
        # Token cache'landi — keyingi yuborishda login takrorlanmaydi
        self.assertEqual(cache.get('eskiz_token'), 'TKN')

    @patch('sms.backends.requests.post')
    def test_send_failure_returns_false(self, mock_post):
        login_resp = MagicMock(status_code=200)
        login_resp.json.return_value = {'data': {'token': 'TKN'}}
        send_resp = MagicMock(status_code=500, text='err')
        mock_post.side_effect = [login_resp, send_resp]
        self.assertFalse(send_sms('+998901234567', 'Kod'))

    @patch('sms.backends.requests.post')
    def test_missing_config_returns_false(self, mock_post):
        with override_settings(SMS_ESKIZ_EMAIL='', SMS_ESKIZ_PASSWORD=''):
            self.assertFalse(send_sms('+998901234567', 'Kod'))
        mock_post.assert_not_called()


class OtpIntegrationTests(TestCase):
    """RegisterView OTP yaratganda send_sms chaqirilishini tekshiradi."""

    @patch('api.views.send_sms', return_value=True)
    def test_register_calls_send_sms(self, mock_send):
        resp = APIClient().post(reverse('api:register'), {
            'phone': '+998901112233', 'password': 'Test12345!', 'name': 'Ali',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(OTPCode.objects.filter(phone='+998901112233').exists())
        mock_send.assert_called_once()
        # Xabar matnida tasdiqlash kodi bo'lishi kerak
        args = mock_send.call_args[0]
        self.assertIn('SamCity', args[1])
