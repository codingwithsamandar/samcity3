"""AI yordamchi — server tomonidagi ovozli javob (bulutli TTS).

Brauzerda haqiqiy o'zbek ovozi yo'q. Shu sabab, agar sozlangan bo'lsa, matnni
bulutli xizmatga yuborib, TAYYOR o'zbek audiosini qaytaramiz — widget uni ijro
etadi. Sozlanmagan bo'lsa `None` qaytadi va widget brauzer ovoziga qaytadi
(xatoyoz emas — muloyim degradatsiya).

Sozlash (env — hammasi ixtiyoriy):
    TTS_PROVIDER   = mohir | azure     (default: bo'sh — o'chiq)

  Mohir.ai / uzbekvoice.ai (o'zbek xizmati):
    MOHIR_TTS_KEY  = <token>           (majburiy)
    MOHIR_TTS_URL  = https://uzbekvoice.ai/api/v1/tts   (kerak bo'lsa o'zgartiriladi)
    MOHIR_TTS_VOICE= <model/ovoz>      (ixtiyoriy)
    MOHIR_TTS_FIELD= text              (so'rov JSON'idagi matn maydoni nomi, default 'text')

  Microsoft Azure:
    AZURE_TTS_KEY  = <kalit>
    AZURE_TTS_REGION = eastus
    TTS_VOICE      = uz-UZ-SardorNeural   (yoki uz-UZ-MadinaNeural)

Natija 1 haftaga keshlanadi (bir xil matn qayta so'ralsa — bepul va tez).
Yangi provayder qo'shish — `_PROVIDERS` ga bitta funksiya.
"""

import hashlib
import os
import urllib.request
from xml.sax.saxutils import escape

from django.core.cache import cache


def provider():
    return os.environ.get('TTS_PROVIDER', '').strip().lower()


def is_enabled():
    p = provider()
    if p == 'azure':
        return bool(os.environ.get('AZURE_TTS_KEY', '').strip())
    if p == 'mohir':
        return bool(os.environ.get('MOHIR_TTS_KEY', '').strip())
    return False


def synthesize(text):
    """Matndan o'zbek audiosi (mp3 baytlar) yoki None. Xatoga chidamli."""
    text = (text or '').strip()
    if not text:
        return None
    fn = _PROVIDERS.get(provider())
    if not fn:
        return None
    voice = os.environ.get('TTS_VOICE', 'uz-UZ-SardorNeural').strip() or 'uz-UZ-SardorNeural'
    key = 'tts:' + hashlib.md5(f'{provider()}|{voice}|{text}'.encode('utf-8')).hexdigest()
    cached = cache.get(key)
    if cached is not None:
        return cached or None  # bo'sh bayt keshlanmasin
    audio = fn(text[:2000], voice)
    if audio:
        cache.set(key, audio, 60 * 60 * 24 * 7)  # 1 hafta
    return audio


def _azure(text, voice):
    region = os.environ.get('AZURE_TTS_REGION', '').strip()
    key = os.environ.get('AZURE_TTS_KEY', '').strip()
    if not (region and key):
        return None
    parts = voice.split('-')
    lang = f'{parts[0]}-{parts[1]}' if len(parts) >= 2 else 'uz-UZ'
    ssml = (f"<speak version='1.0' xml:lang='{lang}'>"
            f"<voice name='{voice}'>{escape(text)}</voice></speak>")
    req = urllib.request.Request(
        f'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1',
        data=ssml.encode('utf-8'), method='POST',
        headers={
            'Ocp-Apim-Subscription-Key': key,
            'Content-Type': 'application/ssml+xml',
            'X-Microsoft-OutputFormat': 'audio-24khz-48kbitrate-mono-mp3',
            'User-Agent': 'SamCity',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except Exception:
        return None


def _mohir(text, voice):
    """Mohir.ai / uzbekvoice.ai — o'zbek TTS.

    Moslashuvchan: endpoint/kalit/maydon env orqali. Javob audio-bayt bo'lsa —
    o'sha; JSON bo'lsa — ichidan audio URL yoki base64 topib oladi.
    """
    import base64
    import json as _json

    url = os.environ.get('MOHIR_TTS_URL', 'https://uzbekvoice.ai/api/v1/tts').strip()
    key = os.environ.get('MOHIR_TTS_KEY', '').strip()
    if not (url and key):
        return None
    field = os.environ.get('MOHIR_TTS_FIELD', 'text').strip() or 'text'
    body = {field: text}
    mv = os.environ.get('MOHIR_TTS_VOICE', '').strip()
    if mv:
        body['model'] = mv

    req = urllib.request.Request(
        url, data=_json.dumps(body).encode('utf-8'), method='POST',
        headers={
            'Authorization': key,
            'Content-Type': 'application/json',
            'User-Agent': 'SamCity',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            ctype = (resp.headers.get('Content-Type') or '').lower()
            raw = resp.read()
    except Exception:
        return None

    # 1) To'g'ridan-to'g'ri audio
    if any(t in ctype for t in ('audio', 'mpeg', 'octet-stream', 'wav', 'ogg')):
        return raw or None
    # 2) JSON — audio URL yoki base64
    try:
        j = _json.loads(raw.decode('utf-8'))
    except Exception:
        return raw or None
    res = j.get('result') if isinstance(j.get('result'), dict) else {}
    audio_url = (j.get('audio_url') or j.get('url') or j.get('audio')
                 or res.get('audio_url') or res.get('url'))
    b64 = j.get('audio_base64') or j.get('base64') or res.get('audio_base64')
    if isinstance(audio_url, str) and audio_url.startswith('http'):
        try:
            with urllib.request.urlopen(audio_url, timeout=20) as ar:
                return ar.read() or None
        except Exception:
            return None
    if isinstance(b64, str) and b64:
        try:
            return base64.b64decode(b64)
        except Exception:
            return None
    return None


# provayder nomi → funksiya. Yangi xizmat qo'shish uchun shu yerga qo'shiladi.
_PROVIDERS = {
    'azure': _azure,
    'mohir': _mohir,
}
