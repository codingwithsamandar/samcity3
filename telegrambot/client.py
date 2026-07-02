"""
Telegram Bot API'ning yupqa (dependency-siz) mijozi — `requests` orqali.

Alohida `python-telegram-bot` paketi shart emas: OTP yuborish uchun bizga
faqat sendMessage/getUpdates/getMe kifoya. Token bo'lmasa — hech narsa qilmaydi
(graceful: log yozadi, xato otmaydi).
"""
import logging

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger('shofirkon.telegram')

API_BASE = 'https://api.telegram.org/bot{token}/{method}'
HTTP_TIMEOUT = 20
_USERNAME_CACHE_KEY = 'telegram_bot_username'


def bot_token() -> str:
    return (getattr(settings, 'TELEGRAM_BOT_TOKEN', '') or '').strip()


def is_configured() -> bool:
    """Token mavjudmi (bot API chaqiruvlari mumkinmi)."""
    return bool(bot_token())


def _call(method: str, payload: dict = None, timeout: int = HTTP_TIMEOUT):
    """Bot API metodini chaqiradi. Muvaffaqiyatda `result`, xatoda None."""
    token = bot_token()
    if not token:
        return None
    url = API_BASE.format(token=token, method=method)
    try:
        resp = requests.post(url, json=payload or {}, timeout=timeout)
        data = resp.json()
        if not data.get('ok'):
            logger.warning('Telegram %s xato: %s', method, data.get('description'))
            return None
        return data.get('result')
    except requests.RequestException as e:
        logger.error('Telegram %s tarmoq xatosi: %s', method, e)
    except Exception as e:  # noqa: BLE001 — OTP oqimi buzilmasin
        logger.exception('Telegram %s kutilmagan xato: %s', method, e)
    return None


def send_message(chat_id, text, reply_markup=None) -> bool:
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup is not None:
        payload['reply_markup'] = reply_markup
    return _call('sendMessage', payload) is not None


def get_updates(offset=None, timeout=25):
    """Long-polling: yangi xabarlarni oladi (polling bot uchun)."""
    payload = {'timeout': timeout}
    if offset is not None:
        payload['offset'] = offset
    # HTTP timeout long-poll timeout'dan biroz katta bo'lsin.
    return _call('getUpdates', payload, timeout=timeout + 10) or []


def get_me():
    return _call('getMe')


def bot_username() -> str:
    """Bot username'i (deep-link uchun). settings yoki getMe orqali, keshlanadi."""
    configured = (getattr(settings, 'TELEGRAM_BOT_USERNAME', '') or '').strip().lstrip('@')
    if configured:
        return configured
    cached = cache.get(_USERNAME_CACHE_KEY)
    if cached:
        return cached
    me = get_me()
    uname = (me or {}).get('username', '') if me else ''
    if uname:
        cache.set(_USERNAME_CACHE_KEY, uname, 24 * 60 * 60)
    return uname
