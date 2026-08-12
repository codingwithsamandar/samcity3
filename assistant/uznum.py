"""Son → o'zbekcha so'z — ovoz (TTS) uchun.

Muammo: TTS «35000» ni raqam sifatida o'qiydi va ko'pincha RUSCHA talaffuz
qiladi («тридцать пять тысяч»). Yechim: ovoz matnidagi sonlarni o'zbekcha SO'Z
bilan almashtiramiz — «35 000 so'm» → «o'ttiz besh ming so'm».

⚠️ FAQAT `speech` (ovoz) matnida qo'llanadi — `ui` (ekran kartalari) da raqam
RAQAM bo'lib qoladi (o'qish qulay). Chaqiriladigan joy: `tts.py` (audio sintezi
oldidan). Ko'lam: 0–9 999 999 (so'm summalari uchun yetarli).
"""

import re

_ONES = ['', 'bir', 'ikki', 'uch', "to'rt", 'besh', 'olti', 'yetti', 'sakkiz', "to'qqiz"]
_TENS = ['', "o'n", 'yigirma', "o'ttiz", 'qirq', 'ellik', 'oltmish', 'yetmish',
         'sakson', "to'qson"]


def _below_thousand(n):
    """0–999 → so'z."""
    parts = []
    h, r = n // 100, n % 100
    if h:
        parts.append('yuz' if h == 1 else _ONES[h] + ' yuz')
    t, o = r // 10, r % 10
    if t:
        parts.append(_TENS[t])
    if o:
        parts.append(_ONES[o])
    return ' '.join(parts)


def uznum(n):
    """Butun sonni o'zbekcha so'zga aylantiradi. Manfiy va 0 ham qo'llanadi."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    if n == 0:
        return 'nol'
    if n < 0:
        return 'minus ' + uznum(-n)

    parts = []
    mil, n = n // 1_000_000, n % 1_000_000
    th, rest = n // 1000, n % 1000
    if mil:
        # mil < 10 (ko'lam 9 999 999), lekin xavfsizlik uchun rekursiya
        parts.append(uznum(mil) + ' million')
    if th:
        parts.append('ming' if th == 1 else _below_thousand(th) + ' ming')
    if rest:
        parts.append(_below_thousand(rest))
    return ' '.join(parts)


# «35 000», «35000», «1 200 000» — probelli yoki probelsiz butun sonlar.
_NUM_RE = re.compile(r'\d[\d\s ]*\d|\d')


def numbers_to_words(text):
    """Matndagi butun sonlarni o'zbekcha so'zga aylantiradi (ovoz uchun).

    O'nlik (8.5) va vaqt (14:30) TEGILMAYDI — faqat butun sonlar. 7 xonadan
    katta sonlar (telefon, yil > 9999999) o'z holicha qoladi.
    """
    def repl(m):
        raw = m.group(0)
        # O'nlik yoki vaqtning bir qismi bo'lsa (oldi/keyingi belgi . yoki :)
        s, e = m.start(), m.end()
        if s > 0 and text[s - 1] in '.,:':
            return raw
        if e < len(text) and text[e] in '.,:':
            return raw
        digits = re.sub(r'[\s ]', '', raw)
        if not digits.isdigit() or len(digits) > 7:
            return raw
        return uznum(int(digits))

    return _NUM_RE.sub(repl, text or '')
