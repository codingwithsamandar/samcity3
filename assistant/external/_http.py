"""Tashqi providerlar uchun umumiy HTTP yordamchisi (requests ustida).

Har bir provider shu yerdagi `get_json` / `get_text` ni ishlatadi — timeout,
User-Agent va xatoga chidamlilik bir joyда. Xato bo'lsa None qaytaradi (provider
buni bo'sh natijaга aylantiradi, chat oqimi buzilmaydi).
"""

import logging

from django.conf import settings

log = logging.getLogger(__name__)

_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')


def _timeout():
    return float(getattr(settings, 'ASSISTANT_EXTERNAL_TIMEOUT', 4))


def get_json(url, params=None, headers=None):
    """URL'dan JSON oladi. Xatoда None."""
    try:
        import requests
    except ImportError:
        log.warning("external: 'requests' topilmadi")
        return None
    h = {'User-Agent': _UA, 'Accept': 'application/json'}
    if headers:
        h.update(headers)
    try:
        r = requests.get(url, params=params, headers=h, timeout=_timeout())
        r.raise_for_status()
        return r.json()
    except Exception as e:  # noqa: BLE001
        log.warning('external GET json xato (%s): %s', url, e)
        return None


def get_text(url, params=None, headers=None):
    """URL'dan matn (HTML) oladi. Xatoда None."""
    try:
        import requests
    except ImportError:
        log.warning("external: 'requests' topilmadi")
        return None
    h = {'User-Agent': _UA,
         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
    if headers:
        h.update(headers)
    try:
        r = requests.get(url, params=params, headers=h, timeout=_timeout())
        r.raise_for_status()
        return r.text
    except Exception as e:  # noqa: BLE001
        log.warning('external GET text xato (%s): %s', url, e)
        return None
