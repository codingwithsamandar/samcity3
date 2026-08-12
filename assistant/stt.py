"""Ovoz→matn (STT) — interfeys. Hozircha brauzer Web Speech ishlatiladi.

⚠️ Bu bo'lakda Mohir.ai ULANMAYDI (kalit yo'q). Bu modul faqat INTERFEYS:
`transcribe()` hozircha None qaytaradi, ya'ni server STT o'chiq. Widget avval
`/ai/stt/` ga urinadi, 204 kelsa brauzer Web Speech'ga qaytadi — bu `tts.py`
dagi bir xil «muloyim degradatsiya» naqshi.

Mohir.ai ulangach FAQAT shu funksiya o'zgaradi: audio olib matn qaytaradi.
Widget'ga tegilmaydi — u allaqachon /ai/stt/ ni sinaydi va tayyor.

SOZLASH (kelajakda — env orqali):
    STT_PROVIDER=mohir       # bo'sh bo'lsa → o'chiq (brauzer)
    STT_API_KEY=...
"""

import os


def provider():
    """Sozlangan STT provayderi ('mohir', ...) yoki bo'sh (o'chiq)."""
    return os.environ.get('STT_PROVIDER', '').strip().lower()


def is_enabled():
    """Server STT yoqilganmi. Hozircha har doim False (Mohir ulanmagan)."""
    return bool(provider()) and bool(os.environ.get('STT_API_KEY', '').strip())


def transcribe(audio_bytes, lang='uz', content_type=''):
    """Ovoz→matn. Muvaffaqiyatda matn (str), aks holda None.

    None → server STT o'chiq yoki tanimadi; chaqiruvchi (view) 204 qaytaradi va
    widget brauzer Web Speech'ga qaytadi.

    Hozircha har doim None — Mohir.ai ulangach shu yerda audio yuboriladi.
    Har qanday xatolik jimgina None qaytaradi (chat/ovoz oqimi buzilmasin).
    """
    if not is_enabled() or not audio_bytes:
        return None
    try:
        prov = provider()
        if prov == 'mohir':
            return _mohir(audio_bytes, lang, content_type)
    except Exception:
        return None
    return None


def _mohir(audio_bytes, lang, content_type):
    """Mohir.ai (uzbekvoice) STT — kelajakda to'ldiriladi.

    Reja: ko'p qismli (multipart) POST bilan audio yuboriladi, javobdan matn
    olinadi. Hozir kalit yo'q, shuning uchun None.
    """
    return None
