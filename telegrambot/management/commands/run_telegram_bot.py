"""Telegram botni polling rejimida ishga tushiradi.

    python manage.py run_telegram_bot

Token bo'lmasa — ishga tushmaydi (xato bermaydi, ogohlantiradi).
Ctrl+C bilan to'xtatiladi.
"""
from django.core.management.base import BaseCommand

from telegrambot.client import is_configured, bot_username
from telegrambot.bot import run_polling


class Command(BaseCommand):
    help = "SamCity Telegram OTP botini polling rejimida ishga tushiradi."

    def handle(self, *args, **opts):
        if not is_configured():
            self._say(self.style.WARNING(
                "TELEGRAM_BOT_TOKEN o'rnatilmagan. Botni ishga tushirib bo'lmaydi.\n"
                "  .env ga TELEGRAM_BOT_TOKEN=... qo'shing va qayta urinib ko'ring."
            ))
            return

        uname = bot_username()
        self._say(self.style.SUCCESS(
            f"Bot ishga tushdi{' (@' + uname + ')' if uname else ''}. "
            "To'xtatish: Ctrl+C"
        ))
        try:
            run_polling()
        except KeyboardInterrupt:
            self._say(self.style.WARNING("Bot to'xtatildi."))

    def _say(self, msg):
        """Windows konsoli (cp1251) UnicodeEncodeError bermasligi uchun xavfsiz yozuv."""
        try:
            self.stdout.write(msg)
        except UnicodeEncodeError:
            self.stdout.write(msg.encode('ascii', 'replace').decode('ascii'))
