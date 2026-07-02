"""
OTP yetkazishning Telegram kanali.

Mavjud OTP mantig'i (kod generatsiyasi, muddat, urinishlar) O'ZGARMAYDI —
faqat yetkazish kanali qo'shiladi. Chaqiruvchi (api/views, main/views) avval
`try_send_telegram()` ni sinaydi; u False qaytarsa mavjud `send_sms()` ishlaydi.
"""
import logging

from django.conf import settings

from sms.backends import normalize_phone
from .client import send_message, is_configured, bot_username

logger = logging.getLogger('shofirkon.telegram')


def telegram_otp_enabled() -> bool:
    """Telegram OTP yoqilganmi (flag + token). Default: DEBUG."""
    enabled = getattr(settings, 'TELEGRAM_OTP_ENABLED', settings.DEBUG)
    return bool(enabled and is_configured())


def _code_text(code: str) -> str:
    return (
        f"🔐 <b>SamCity</b> tasdiqlash kodingiz:\n\n"
        f"<code>{code}</code>\n\n"
        f"Kod 10 daqiqa ichida amal qiladi. Uni hech kimga bermang."
    )


def try_send_telegram(phone: str, code: str) -> bool:
    """Agar raqam Telegram'ga ulangan bo'lsa — kodni Telegram orqali yuboradi.

    Muvaffaqiyatda True (kanal = telegram), aks holda False (SMS'ga qaytiladi).
    """
    if not telegram_otp_enabled():
        return False
    # Modelni funksiya ichida import qilamiz (ilova yuklanish tartibi xavfsizligi).
    from .models import TelegramLink
    norm = normalize_phone(phone)
    link = TelegramLink.objects.filter(phone=norm).first()
    if not link:
        return False
    if send_message(link.chat_id, _code_text(code)):
        logger.info('OTP Telegram orqali yuborildi: %s', norm)
        return True
    return False


def telegram_connect_url():
    """Botni ulash uchun deep-link (t.me/<bot>), yoki None (agar sozlanmagan)."""
    if not telegram_otp_enabled():
        return None
    uname = bot_username()
    return f'https://t.me/{uname}' if uname else None
