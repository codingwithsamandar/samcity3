"""Joy qidiruvi — transliteratsiya va xatoga chidamli moslashtirish.

Nega alohida modul: qidiruv uch joyda ishlatiladi (xarita, «Yaqinimda»,
joylar katalogi) va ularda bir xil qoida bo'lishi shart. Ilgari xaritada
mijoz tomonida `name.includes()` bor edi — u manzilni ko'rmasdi, kirillcha
yozuvni topmasdi va bitta harf xato bo'lsa hech narsa qaytarmasdi.
"""
from difflib import SequenceMatcher

# ── O'zbek kirill → lotin ────────────────────────────────────────────────────
# Ko'p harfli almashinuvlar avval turishi SHART: 'ш'→'sh' bir harfli
# qoidalardan oldin qo'llanmasa, natija buziladi.
_CYR_MAP = [
    ('ё', 'yo'), ('ж', 'j'), ('ц', 'ts'), ('ч', 'ch'), ('ш', 'sh'),
    ('щ', 'sh'), ('ю', 'yu'), ('я', 'ya'), ('ў', 'o'), ('қ', 'q'),
    ('ғ', 'g'), ('ҳ', 'h'), ('ъ', ''), ('ь', ''),
    ('а', 'a'), ('б', 'b'), ('в', 'v'), ('г', 'g'), ('д', 'd'),
    ('е', 'e'), ('з', 'z'), ('и', 'i'), ('й', 'y'), ('к', 'k'),
    ('л', 'l'), ('м', 'm'), ('н', 'n'), ('о', 'o'), ('п', 'p'),
    ('р', 'r'), ('с', 's'), ('т', 't'), ('у', 'u'), ('ф', 'f'),
    ('х', 'x'), ('ы', 'i'), ('э', 'e'),
]

# Lotin yozuvidagi bir xil tovushning turli yozilishi — bitta shaklga.
# "Xolboyev"/"Holboyev", "Aziz"/"Azis" kabi juftlar shu bilan uchrashadi.
_LAT_MAP = [
    ("o'", 'o'), ('oʻ', 'o'), ('o‘', 'o'), ("g'", 'g'), ('gʻ', 'g'), ('g‘', 'g'),
    ('sh', 's'), ('ch', 'c'), ('ts', 's'), ('yo', 'o'), ('yu', 'u'), ('ya', 'a'),
    ('kh', 'x'), ('h', 'x'), ('w', 'v'), ('q', 'k'), ('z', 's'), ('j', 'c'),
]

_KEEP = set('abcdefghijklmnopqrstuvwxyz0123456789 ')


def normalize(text):
    """Qidiruv uchun yagona shaklga keltiradi.

    Kirill → lotin, apostrofli harflar sodda shaklga, tovushdosh harflar
    birlashtiriladi, tinish belgilari olib tashlanadi.

        normalize('Навоий кўчаси') == normalize("Navoiy ko'chasi")
    """
    if not text:
        return ''
    t = text.casefold()
    for a, b in _CYR_MAP:
        t = t.replace(a, b)
    for a, b in _LAT_MAP:
        t = t.replace(a, b)
    t = ''.join(ch if ch in _KEEP else ' ' for ch in t)
    return ' '.join(t.split())


def _fuzzy(needle, hay):
    """Xato yozuvga chidamli o'xshashlik (0..1).

    So'zma-so'z tekshiradi: uzun matnda bitta so'z mos kelsa yetarli,
    aks holda uzun manzil qisqa so'rovni hech qachon topmaydi.
    """
    best = SequenceMatcher(None, needle, hay).ratio()
    for word in hay.split():
        if abs(len(word) - len(needle)) <= 3:
            best = max(best, SequenceMatcher(None, needle, word).ratio())
    return best


def score(query, *fields):
    """Joyning so'rovga mosligi (0 = mos emas, katta = yaxshiroq).

    Bosqichma-bosqich: aniq boshlanish > ichida bor > xatoga chidamli.
    Shu tartib natijalarni ham saralaydi.
    """
    q = normalize(query)
    if not q:
        return 0.0
    best = 0.0
    for raw in fields:
        hay = normalize(raw)
        if not hay:
            continue
        if hay.startswith(q):
            best = max(best, 1.0)
        elif q in hay:
            best = max(best, 0.9)
        elif any(w.startswith(q) for w in hay.split()):
            best = max(best, 0.85)
        else:
            # Xato yozuv — faqat yetarlicha uzun so'rovlar uchun, aks holda
            # ikki harfli so'rov butun bazani qaytarib yuboradi.
            if len(q) >= 4:
                r = _fuzzy(q, hay)
                if r >= 0.72:
                    best = max(best, r * 0.8)
    return best


def search_places(queryset, query, limit=30):
    """Joylarni moslik bo'yicha saralab qaytaradi: [(place, ball), ...]."""
    if not (query or '').strip():
        return []
    rows = []
    for p in queryset:
        s = score(query, p.name, p.name_ru, p.name_en,
                  p.address, p.get_category_display())
        if s:
            rows.append((p, s))
    rows.sort(key=lambda x: -x[1])
    return rows[:limit]
