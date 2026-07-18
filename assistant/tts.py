"""AI yordamchi — server tomonidagi ovozli javob (bulutli TTS).

Brauzerda haqiqiy o'zbek ovozi yo'q. Shu sabab, agar sozlangan bo'lsa, matnni
bulutli xizmatga yuborib, TAYYOR o'zbek audiosini qaytaramiz — widget uni ijro
etadi. Sozlanmagan bo'lsa `None` qaytadi va widget brauzer ovoziga qaytadi
(xatoyoz emas — muloyim degradatsiya).

Sozlash (env — hammasi ixtiyoriy):
    TTS_PROVIDER   = azure         (default: bo'sh — o'chiq)
    AZURE_TTS_KEY  = <kalit>
    AZURE_TTS_REGION = eastus      (Azure resurs regioni)
    TTS_VOICE      = uz-UZ-SardorNeural   (yoki uz-UZ-MadinaNeural)

Natija 1 haftaga keshlanadi (bir xil matn qayta so'ralsa — bepul va tez).
Yangi provayder (masalan Mohir.ai) qo'shish — `_PROVIDERS` ga bitta funksiya.
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


# provayder nomi → funksiya. Yangi xizmat qo'shish uchun shu yerga qo'shiladi.
_PROVIDERS = {
    'azure': _azure,
}
