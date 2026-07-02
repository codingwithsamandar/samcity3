"""
Polling rejimidagi bot logikasi (webhook'siz — demo uchun yetarli).

Ikki hodisa:
  /start           → tushuntirish + "📱 Raqamni ulashish" (request_contact) tugmasi
  contact xabari   → Telegram tasdiqlagan raqam + chat_id ni TelegramLink'ga saqlaydi

Raqamni ulash — Telegram tomonidan tasdiqlangan (KeyboardButton request_contact),
shuning uchun qo'shimcha tekshiruv shart emas.
"""
import logging
import time

from django.core.cache import cache

from sms.backends import normalize_phone
from .client import send_message, is_configured, get_updates

logger = logging.getLogger('shofirkon.telegram')

_OFFSET_CACHE_KEY = 'telegram_updates_offset'

CONTACT_KEYBOARD = {
    'keyboard': [[{'text': '📱 Raqamni ulashish', 'request_contact': True}]],
    'resize_keyboard': True,
    'one_time_keyboard': True,
}
REMOVE_KEYBOARD = {'remove_keyboard': True}

START_TEXT = (
    "👋 Assalomu alaykum! Bu — <b>SamCity</b> tasdiqlash boti.\n\n"
    "Ro'yxatdan o'tish/kirish kodini SMS o'rniga shu Telegram orqali olish uchun "
    "quyidagi <b>«📱 Raqamni ulashish»</b> tugmasini bosing.\n\n"
    "Raqamingiz faqat kod yuborish uchun ishlatiladi."
)


def _handle_start(chat_id):
    send_message(chat_id, START_TEXT, reply_markup=CONTACT_KEYBOARD)


def _handle_contact(message):
    contact = message['contact']
    chat_id = message['chat']['id']
    # Faqat foydalanuvchining O'ZI ulashgan raqamini qabul qilamiz
    # (boshqaning kontaktini yuborsa — user_id mos kelmaydi).
    from_id = message.get('from', {}).get('id')
    if contact.get('user_id') and from_id and contact['user_id'] != from_id:
        send_message(chat_id, "Iltimos, o'zingizning raqamingizni ulashing.",
                     reply_markup=CONTACT_KEYBOARD)
        return

    phone = normalize_phone(contact.get('phone_number', ''))
    if not phone:
        send_message(chat_id, "Raqamni o'qib bo'lmadi. Qayta urinib ko'ring.",
                     reply_markup=CONTACT_KEYBOARD)
        return

    username = message.get('from', {}).get('username', '') or ''
    from .models import TelegramLink
    link, created = TelegramLink.objects.get_or_create(
        phone=phone, defaults={'chat_id': chat_id, 'telegram_username': username})
    if not created:
        # Idempotent: chat_id/username yangilanadi, lekin "allaqachon" deb aytamiz.
        link.chat_id = chat_id
        link.telegram_username = username
        link.save(update_fields=['chat_id', 'telegram_username', 'linked_at'])
        send_message(chat_id,
                     "ℹ️ Siz allaqachon ulangansiz. Endi kodlar shu yerga keladi.",
                     reply_markup=REMOVE_KEYBOARD)
        return

    send_message(chat_id,
                 "✅ Raqamingiz ulandi! Endi saytda/ilovada shu raqam bilan kirsangiz, "
                 "tasdiqlash kodi shu Telegram orqali keladi.",
                 reply_markup=REMOVE_KEYBOARD)
    logger.info('Telegram ulandi: %s (chat %s)', phone, chat_id)


def handle_update(update: dict):
    """Bitta Telegram update'ini qayta ishlaydi."""
    message = update.get('message') or update.get('edited_message')
    if not message:
        return
    if 'contact' in message:
        _handle_contact(message)
        return
    text = (message.get('text') or '').strip()
    if text.startswith('/start'):
        _handle_start(message['chat']['id'])
    elif text:
        # Boshqa har qanday matn — yo'riqnoma
        send_message(message['chat']['id'],
                     "Kodni olish uchun «📱 Raqamni ulashish» tugmasini bosing yoki /start yuboring.",
                     reply_markup=CONTACT_KEYBOARD)


def run_polling(stop_check=None):
    """getUpdates long-polling sikli. `stop_check()` True qaytarsa to'xtaydi."""
    if not is_configured():
        raise RuntimeError("TELEGRAM_BOT_TOKEN o'rnatilmagan — bot ishga tushmaydi.")
    offset = cache.get(_OFFSET_CACHE_KEY)
    logger.info('Telegram bot polling boshlandi (offset=%s)', offset)
    while True:
        if stop_check and stop_check():
            break
        updates = get_updates(offset=offset, timeout=25)
        for upd in updates:
            try:
                handle_update(upd)
            except Exception:  # noqa: BLE001 — bitta xato butun sikl'ni to'xtatmasin
                logger.exception('Update qayta ishlashda xato: %s', upd.get('update_id'))
            offset = upd['update_id'] + 1
            cache.set(_OFFSET_CACHE_KEY, offset, 7 * 24 * 60 * 60)
        if not updates:
            time.sleep(1)
