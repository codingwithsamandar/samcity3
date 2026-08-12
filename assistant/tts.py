"""AI yordamchi — server tomonidagi ovozli javob (bulutli TTS).

Brauzerda haqiqiy o'zbek ovozi yo'q. Shu sabab, agar sozlangan bo'lsa, matnni
bulutli xizmatga yuborib, TAYYOR o'zbek audiosini qaytaramiz — widget uni ijro
etadi. Sozlanmagan bo'lsa `None` qaytadi va widget brauzer ovoziga qaytadi
(xatoyoz emas — muloyim degradatsiya).

Sozlash (env):
    TTS_PROVIDER = aisha | azure       (bo'sh bo'lsa — o'chiq)

  Aisha AI (aisha.group — o'zbek xizmati, TAVSIYA ETILADI):
    AISHA_API_KEY  = <kalit>           (space.aisha.group → API keys)
    AISHA_TTS_MODEL= Gulnoza           (ixtiyoriy)
    AISHA_TTS_MOOD = Neutral           (Neutral | Cheerful | Happy | Sad)
    AISHA_TTS_SPEED= 1.0               (0.5–2.0)

  Microsoft Azure:
    AZURE_TTS_KEY  = <kalit>
    AZURE_TTS_REGION = eastus
    TTS_VOICE      = uz-UZ-SardorNeural

ESLATMA: Mohir / UzbekVoice.ai — faqat STT (ovoz→matn) xizmati, unda TTS yo'q.

Natija 1 haftaga keshlanadi (bir xil matn qayta so'ralsa — bepul va tez).
"""

import hashlib
import os
import urllib.request
from xml.sax.saxutils import escape

from django.core.cache import cache

AISHA_BASE = 'https://back.aisha.group'
# Aisha transcript uzunlik chegarasi (kalit bilan) — hujjatga ko'ra 1000 belgi.
AISHA_MAX_CHARS = 1000


def provider():
    return os.environ.get('TTS_PROVIDER', '').strip().lower()


def is_enabled():
    p = provider()
    if p == 'aisha':
        return bool(os.environ.get('AISHA_API_KEY', '').strip())
    if p == 'azure':
        return bool(os.environ.get('AZURE_TTS_KEY', '').strip())
    return False


def content_type():
    """Qaytarilayotgan audio turi (provayderga qarab)."""
    return 'audio/wav' if provider() == 'aisha' else 'audio/mpeg'


def synthesize(text):
    """Matndan o'zbek audiosi (baytlar) yoki None. Xatoga chidamli."""
    text = (text or '').strip()
    if not text:
        return None
    # ⚠️ Sonlarni o'zbekcha so'zga aylantiramiz — aks holda TTS «35000» ni
    # ruscha o'qiydi. Bu FAQAT ovozga ta'sir qiladi (ui/ekran raqamni saqlaydi).
    try:
        from .uznum import numbers_to_words
        text = numbers_to_words(text)
    except Exception:
        pass
    fn = _PROVIDERS.get(provider())
    if not fn:
        return None
    voice = os.environ.get('TTS_VOICE', 'uz-UZ-SardorNeural').strip() or 'uz-UZ-SardorNeural'
    key = 'tts:' + hashlib.md5(f'{provider()}|{voice}|{text}'.encode('utf-8')).hexdigest()
    cached = cache.get(key)
    if cached is not None:
        return cached or None
    audio = fn(text, voice)
    if audio:
        cache.set(key, audio, 60 * 60 * 24 * 7)  # 1 hafta
    return audio


# ─── Aisha AI (aisha.group) ──────────────────────────────────────────────────
def _aisha(text, voice):
    """POST /api/v1/tts/post/ (multipart) → {"audio_path": "..."} → WAV yuklab olinadi."""
    import requests  # requirements.txt da bor

    key = os.environ.get('AISHA_API_KEY', '').strip()
    if not key:
        return None
    url = os.environ.get('AISHA_TTS_URL', f'{AISHA_BASE}/api/v1/tts/post/').strip()
    transcript = text[:AISHA_MAX_CHARS]

    # Kirill matn bo'lsa — ruscha oqim (hujjat: en/ru uchun model/mood/speed YUBORILMAYDI)
    is_cyr = any('Ѐ' <= ch <= 'ӿ' for ch in transcript)
    fields = {
        'transcript': (None, transcript),
        'language': (None, 'ru' if is_cyr else 'uz'),
    }
    if not is_cyr:
        fields['model'] = (None, os.environ.get('AISHA_TTS_MODEL', 'Gulnoza').strip() or 'Gulnoza')
        fields['mood'] = (None, os.environ.get('AISHA_TTS_MOOD', 'Neutral').strip() or 'Neutral')
        fields['speed'] = (None, os.environ.get('AISHA_TTS_SPEED', '1.0').strip() or '1.0')

    try:
        r = requests.post(url, headers={'X-Api-Key': key}, files=fields, timeout=30)
        if r.status_code not in (200, 201):
            return None
        data = r.json()
    except Exception:
        return None

    path = data.get('audio_path') or data.get('audio_url')
    if not path:
        return None
    audio_url = path if path.startswith('http') else f'{AISHA_BASE}{path}'
    try:
        a = requests.get(audio_url, headers={'X-Api-Key': key}, timeout=30)
        if a.status_code != 200:
            return None
        return a.content or None
    except Exception:
        return None


# ─── Microsoft Azure ─────────────────────────────────────────────────────────
def _azure(text, voice):
    region = os.environ.get('AZURE_TTS_REGION', '').strip()
    key = os.environ.get('AZURE_TTS_KEY', '').strip()
    if not (region and key):
        return None
    parts = voice.split('-')
    lang = f'{parts[0]}-{parts[1]}' if len(parts) >= 2 else 'uz-UZ'
    ssml = (f"<speak version='1.0' xml:lang='{lang}'>"
            f"<voice name='{voice}'>{escape(text[:2000])}</voice></speak>")
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
    'aisha': _aisha,
    'azure': _azure,
}
