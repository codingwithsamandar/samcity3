"""Demo uchun telefon ↔ Telegram chat'ni QO'LDA ulash.

    python manage.py link_telegram_demo --phone=+998900000011 --chat-id=123456789

Botga /start yozib "Raqamni ulashish" tugmasidan foydalanmasdan, o'z chat_id'ingizni
bilib turib demo userga ulash uchun (masalan @userinfobot yordamida chat_id topib).
"""
from django.core.management.base import BaseCommand, CommandError

from sms.backends import normalize_phone
from telegrambot.models import TelegramLink


class Command(BaseCommand):
    help = "Demo: telefon raqamni Telegram chat_id ga qo'lda ulaydi."

    def add_arguments(self, parser):
        parser.add_argument('--phone', required=True, help="Telefon (masalan +998900000011)")
        parser.add_argument('--chat-id', required=True, type=int, help="Telegram chat ID (raqam)")
        parser.add_argument('--username', default='', help="Telegram username (ixtiyoriy)")

    def handle(self, *args, **opts):
        phone = normalize_phone(opts['phone'])
        if not phone:
            raise CommandError("Telefon raqami noto'g'ri.")
        link, created = TelegramLink.objects.update_or_create(
            phone=phone,
            defaults={'chat_id': opts['chat_id'],
                      'telegram_username': (opts['username'] or '').lstrip('@')},
        )
        action = 'yaratildi' if created else 'yangilandi'
        self.stdout.write(self.style.SUCCESS(
            f"✅ Bog'lanish {action}: {phone} → chat {link.chat_id}\n"
            f"   Endi shu raqam bilan kirsangiz, OTP Telegram orqali keladi."
        ))
