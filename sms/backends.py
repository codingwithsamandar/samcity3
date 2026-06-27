"""
SamCity SMS shlyuzi — O'zbek provayderlari.

Umumiy kirish nuqtasi: send_sms(phone, text) -> bool
  - Hech qachon exception otmaydi (xatoda False qaytaradi), shu sabab OTP
    oqimini buzmaydi.
  - Provayder .env dagi SMS_BACKEND bilan tanlanadi:
      eskiz      → Eskiz.uz (notify.eskiz.uz)
      playmobile → Playmobile (send.smsxabar.uz)
      console    → faqat log/print (development; DEBUG=True da ham shu)

Sozlamalar (settings.py / .env):
  SMS_BACKEND, SMS_ESKIZ_EMAIL, SMS_ESKIZ_PASSWORD, SMS_ESKIZ_FROM,
  SMS_PLAYMOBILE_LOGIN, SMS_PLAYMOBILE_PASSWORD, SMS_PLAYMOBILE_FROM
"""
import logging
import uuid

import requests
from django.conf import settings
from django.core.cache import cache

from .exceptions import SMSAuthError, SMSConfigError

logger = logging.getLogger('shofirkon.sms')

ESKIZ_BASE = 'https://notify.eskiz.uz/api'
ESKIZ_TOKEN_CACHE_KEY = 'eskiz_token'
ESKIZ_TOKEN_TTL = 23 * 60 * 60  # 23 soat (token 24 soat amal qiladi)
PLAYMOBILE_URL = 'https://send.smsxabar.uz/broker-api/send'
HTTP_TIMEOUT = 15


def normalize_phone(phone: str) -> str:
    """Telefonni '998XXXXXXXXX' ko'rinishiga keltiradi (+, bo'shliq, - tozalanadi)."""
    digits = ''.join(ch for ch in str(phone) if ch.isdigit())
    if digits.startswith('998'):
        return digits
    if len(digits) == 9:               # XXXXXXXXX → 998XXXXXXXXX
        return '998' + digits
    if digits.startswith('8') and len(digits) == 12:  # 8XX... kabi holatlar
        return '998' + digits[-9:]
    return digits


def _setting(name: str, default: str = '') -> str:
    return (getattr(settings, name, default) or '').strip()


def send_sms(phone: str, text: str) -> bool:
    """OTP/xabar yuboradi. Muvaffaqiyatda True, xatoda False (exception yo'q)."""
    backend = _setting('SMS_BACKEND', 'console').lower()
    msisdn = normalize_phone(phone)
    try:
        if backend == 'eskiz':
            return _eskiz_send(msisdn, text)
        if backend == 'playmobile':
            return _playmobile_send(msisdn, text)
        return _console_send(msisdn, text)
    except (SMSAuthError, SMSConfigError) as e:
        logger.error("SMS config/auth xatosi (%s): %s", backend, e)
    except requests.RequestException as e:
        logger.error("SMS tarmoq xatosi (%s): %s", backend, e)
    except Exception as e:  # noqa: BLE001 — OTP oqimi hech qachon buzilmasin
        logger.exception("SMS kutilmagan xato (%s): %s", backend, e)
    return False


# ─────────────────────────── Console (dev) ───────────────────────────
def _console_send(phone: str, text: str) -> bool:
    # ASCII '->' (Unicode strelka Windows cp1251 konsolida UnicodeEncodeError beradi)
    logger.info("[CONSOLE SMS] %s -> %s", phone, text)
    print(f"[CONSOLE SMS] {phone} -> {text}")
    return True


# ─────────────────────────── Eskiz.uz ───────────────────────────
def _eskiz_token(force_refresh: bool = False) -> str:
    if not force_refresh:
        cached = cache.get(ESKIZ_TOKEN_CACHE_KEY)
        if cached:
            return cached
    email = _setting('SMS_ESKIZ_EMAIL')
    password = _setting('SMS_ESKIZ_PASSWORD')
    if not email or not password:
        raise SMSConfigError('SMS_ESKIZ_EMAIL / SMS_ESKIZ_PASSWORD to\'ldirilmagan')
    resp = requests.post(
        f'{ESKIZ_BASE}/auth/login',
        data={'email': email, 'password': password},
        timeout=HTTP_TIMEOUT,
    )
    if resp.status_code != 200:
        raise SMSAuthError(f'Eskiz login xatosi: {resp.status_code} {resp.text[:200]}')
    token = (resp.json().get('data') or {}).get('token')
    if not token:
        raise SMSAuthError('Eskiz javobida token yo\'q')
    cache.set(ESKIZ_TOKEN_CACHE_KEY, token, ESKIZ_TOKEN_TTL)
    return token


def _eskiz_send(phone: str, text: str) -> bool:
    sender = _setting('SMS_ESKIZ_FROM', '4546')
    token = _eskiz_token()
    payload = {'mobile_phone': phone, 'message': text, 'from': sender}

    def _post(tok):
        return requests.post(
            f'{ESKIZ_BASE}/message/sms/send',
            data=payload,
            headers={'Authorization': f'Bearer {tok}'},
            timeout=HTTP_TIMEOUT,
        )

    resp = _post(token)
    if resp.status_code == 401:  # token eskirgan — bir marta yangilab qayta urinamiz
        token = _eskiz_token(force_refresh=True)
        resp = _post(token)
    if resp.status_code in (200, 201):
        logger.info("Eskiz SMS yuborildi: %s", phone)
        return True
    logger.error("Eskiz SMS xatosi: %s %s", resp.status_code, resp.text[:200])
    return False


# ─────────────────────────── Playmobile ───────────────────────────
def _playmobile_send(phone: str, text: str) -> bool:
    login = _setting('SMS_PLAYMOBILE_LOGIN')
    password = _setting('SMS_PLAYMOBILE_PASSWORD')
    if not login or not password:
        raise SMSConfigError('SMS_PLAYMOBILE_LOGIN / SMS_PLAYMOBILE_PASSWORD to\'ldirilmagan')
    originator = _setting('SMS_PLAYMOBILE_FROM', '3700')
    payload = {
        'messages': [{
            'recipient': phone,
            'message-id': uuid.uuid4().hex,
            'sms': {'originator': originator, 'content': {'text': text}},
        }],
    }
    resp = requests.post(
        PLAYMOBILE_URL, json=payload,
        auth=(login, password), timeout=HTTP_TIMEOUT,
    )
    if resp.status_code in (200, 201):
        logger.info("Playmobile SMS yuborildi: %s", phone)
        return True
    logger.error("Playmobile SMS xatosi: %s %s", resp.status_code, resp.text[:200])
    return False
