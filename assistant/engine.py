"""SamCity AI yordamchisining "miya"si — mahalliy NLU (til tushunish) dvigateli.

Tashqi API'siz, faqat kalit so'zlar, fuzzy (xatoga chidamli) moslash va bazadagi
real ma'lumot bilan ishlaydi. Foydalanuvchi savolini (o'zbek/rus/ingliz) tahlil
qilib, niyatini (intent) aniqlaydi va boy javob — matn + kartalar (masofa, piyoda
vaqti, telefon, yo'nalish, ochiq/yopiq, reyting) + havolalar — tayyorlaydi.

Xususiyatlar:
  • Fuzzy moslash — "dorxona", "aptaka" kabi xatolarni ham tushunadi.
  • Suhbatni davom ettirish — "yana", "boshqa" desa keyingi variantlarni beradi.
  • Kontekst — oldingi toifa va offset klient tomonidan uzatiladi.
  • Ochiq/yopiq — ish vaqtini joriy (Toshkent) vaqt bilan solishtiradi.

Agar mahalliy dvigatel tushunmasa `intent='unknown'` qaytaradi — views.py uni
ixtiyoriy LLM (llm.py) ga uzatadi. Hech qanday migratsiya/model kerak emas.
"""

import difflib
import math
import re

from django.conf import settings


# ─── Xarita markazi (foydalanuvchi joylashuvi bo'lmasa — shu ishlatiladi) ─────
CENTER = (40.1156, 64.5036)  # Shofirkon shahri markazi (places/views.py bilan bir xil)

WALK_KMH = 4.6   # o'rtacha piyoda tezligi
DRIVE_KMH = 22.0  # shahar ichida mashina (places route_api bilan bir xil)


def _haversine(lat1, lon1, lat2, lon2):
    """Ikki koordinata orasidagi masofa (km)."""
    R = 6371.0
    try:
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) *
             math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    except (TypeError, ValueError):
        return 1e9


def _norm(text):
    """Solishtirishga tayyorlash: kichik harf va BARCHA apostroflarni olib tashlash.

    O'zbekchada apostrof (tutuq belgisi) har xil yoziladi — oʻ/o', gʻ/g', hamda
    "e'lon", "ma'lumot" kabi so'zlarda. Har xil belgilarni (ʻ ʼ ' ` …) avval bitta
    ' ga keltiramiz, so'ng butunlay olib tashlaymiz. Natijada "e'lon"→"elon",
    "do'kon"→"dokon", "gʻisht"→"gisht" — kalit so'zlar (apostrofsiz) bilan mos keladi.
    """
    if not text:
        return ''
    t = text.lower().strip()
    for ch in ('ʻ', 'ʼ', '‘', '’', '`', '´'):
        t = t.replace(ch, "'")
    t = t.replace("'", "")  # barcha apostroflarni olib tashlaymiz
    return t


def _fmt_dist(km):
    """Masofani odam o'qiydigan ko'rinishda: 850 m yoki 1.2 km."""
    if km < 1:
        return f'{int(round(km * 1000))} m'
    return f'{km:.1f} km'.replace('.0 km', ' km')


def _walk_min(km):
    return max(1, round(km / WALK_KMH * 60))


def _drive_min(km):
    return max(1, round(km / DRIVE_KMH * 60))


# ─── Toifa (kategoriya) kalit so'zlari ────────────────────────────────────────
CATEGORY_KEYWORDS = {
    'pharmacy':     ['dorixona', 'dori', 'apteka', 'аптека', 'pharmacy', 'drugstore'],
    'hospital':     ['shifoxona', 'kasalxona', 'poliklinika', 'shifokor', 'vrach',
                     'doktor', 'больница', 'госпиталь', 'поликлиника', 'врач',
                     'hospital', 'clinic', 'tibbiyot', 'tez yordam', 'skoraya'],
    'bank':         ['bank', 'банк', 'bankomat', 'банкомат', 'atm'],
    'post':         ['pochta', 'почта', 'post'],
    'restaurant':   ['restoran', 'kafe', 'oshxona', 'choyxona', 'ресторан', 'кафе',
                     'restaurant', 'cafe', 'ovqatlanish', 'taomnoma', 'fastfud'],
    'hotel':        ['mehmonxona', 'гостиница', 'отель', 'hotel', 'hostel'],
    'wedding':      ['toyxona', 'свадьба', 'wedding', "to'y qil", 'zal band',
                     "to'yxona kerak", 'toy zali'],
    'school':       ['maktab', 'школа', 'school', 'litsey'],
    'kindergarten': ['bogcha', 'детсад', 'садик', 'kindergarten', 'yasli'],
    'barber':       ['sartarosh', 'sartaroshxona', 'soch oldirish', 'soch ol',
                     'soch kes', 'soch qildir', 'soch oldir', 'sochimni oldir',
                     'парикмахер', 'barber'],
    'government':   ['hokimlik', 'hokimiyat', 'davlat', 'mahkama', 'администрация',
                     'хокимият', 'idora', 'fuqarolar yig'],
    'organization': ['tashkilot', 'ofis', 'kompaniya', 'офис', 'организация', 'office'],
    'furniture':    ['mebel', 'мебель', 'furniture', 'divan', 'shkaf'],
    'electronics':  ['elektronika', 'texnika', 'электроника', 'electronics',
                     'kompyuter', 'noutbuk'],
    'tourist':      ['diqqatga sazovor', 'sayohat', 'muzey', 'yodgorlik',
                     'достопримечательн', 'туризм', 'tourist', 'maqbara',
                     'tarixiy joy', 'ziyorat'],
}

VALID_CATEGORIES = set(CATEGORY_KEYWORDS.keys())

CATEGORY_LABEL = {
    'pharmacy': ('Dorixona', '💊'), 'hospital': ('Shifoxona', '🏥'),
    'bank': ('Bank', '🏦'), 'post': ('Pochta', '✉️'),
    'restaurant': ('Restoran/Kafe', '🍽️'), 'hotel': ('Mehmonxona', '🏨'),
    'wedding': ("To'yxona", '💍'), 'school': ('Maktab', '🏫'),
    'kindergarten': ("Bog'cha", '🧸'), 'barber': ('Sartaroshxona', '💈'),
    'government': ('Davlat binosi', '🏛️'), 'organization': ('Tashkilot', '🏢'),
    'furniture': ("Mebel do'koni", '🛋️'), 'electronics': ('Elektronika', '📱'),
    'tourist': ('Diqqatga sazovor joy', '🗺️'),
}

# ─── Niyat belgilari ──────────────────────────────────────────────────────────
NEAR_WORDS = ['yaqin', 'yonim', 'atrofim', 'qayerda', 'qaerda', 'topib ber',
              'korsat', 'boradigan', 'near', 'nearest', 'closest', 'where',
              'ближайш', 'рядом', 'близко', 'где', 'найти', 'найди']
CONTINUE_WORDS = ['yana', 'boshqa', 'davom', 'yene', 'yena', 'ещё', 'еще',
                  'more', 'boshqasi', 'keyingi', 'qolganlari']
TAXI_WORDS = ['taksi', 'taxi', 'такси', 'mashina chaqir', 'moshina chaqir',
              'haydovchi', 'yol haqi', 'yolga chiqaman']
DELIVERY_WORDS = ['yetkaz', 'dostavka', 'доставка', 'dokon', 'магазин', 'market',
                  'buyurtma ber', 'zakaz', 'mahsulot', 'oziq-ovqat', 'produkt',
                  'delivery', 'savat']
# ⚠️ 'sotuv' OLIB TASHLANDI — u «sotuvchi» (kasb) bilan noto'g'ri mos kelib,
# ish qidiruvини e'lonlar bo'limiga yuborardi. «sotuvda» aniqroq (sotuvchi'ga
# tushmaydi). 'sotaman' esa ACTION_INTENT'да → agent hal qiladi.
ADS_WORDS = ['elon', 'sotib olaman', 'sotaman', 'sotib ber', 'sotuvda',
             'ijaraga', 'ijara', 'объявлен', 'куплю', 'продам', 'e lon',
             'marketplace', 'mashina sotib', 'uy sotib']
JOB_WORDS = ['ish topish', 'ish kerak', 'ish orni', 'vakansiya', 'vacancy',
             'работа', 'вакансия', 'rezyume', 'resume', 'ishga joylash']
BOOKING_WORDS = ['bron', 'band qil', 'joy band', 'бронир', 'booking', 'zal band',
                 'stol band']

# ── HARAKAT (amal) NIYATI ─────────────────────────────────────────────────────
# «bron qil», «buyurtma qil», «yozib qo'y», «soch oldir» — bu JOY TOPISH emas,
# biror ishni BAJARISH. Bunday so'rovда engine chekinadi (intent='unknown') va
# agent (booking/delivery) hal qiladi. Aks holда category (barber/restaurant)
# yoki delivery/booking branchи agentни SOYA qiladi (PROMPT_9 ildizи).
# ⚠️ BOOKING_WORDS qayta ishlatiladi (bron/band qil) + kengaytiriladi.
ACTION_INTENT_WORDS = BOOKING_WORDS + [
    'joy bron', 'yozib qoy', 'yozib ber', 'sartaroshga yozil',
    'buyurtma', 'zakaz', 'order',
    'soch oldir', 'oldirmoqchi',
    # delivery (buyurtма/yetkazib berish AMALI — «do'kon qayerda» search'i emas)
    # «somsa yetkazib bering», «lavash olib keling», «ovqat yetkaz» → agent.
    'yetkazib ber', 'yetkaz', 'olib kel', 'olib keling',
    # taxi (chaqirish amali — «taksi qayerda» search'i emas)
    'taksi chaqir', 'taksi kerak', 'taksi buyur',
    # booking: to'yxona/zal KUNLIK bron amali. ⚠️ Faqat «kerak/bron» bilan —
    # yolg'iz «toyxona» qo'shilsa «to'yxona qayerda» (manzil so'rovi) ham
    # agentga ketib, bepul places branch'ini soya qilardi.
    'toyxona kerak', 'toyxona bron', 'toyxona band', 'zal kerak', 'zal bron',
    # ads (YANGI e'lon joylash — «sotib olaman» search'i emas)
    'elon joylash', 'elon joylashtir', 'elon qosh', 'sotaman', 'sotmoqchiman',
    # jobs (joylash / xodim qidirish amali)
    'vakansiya joylash', 'xodim kerak', 'ishchi kerak', 'rezyume joylash',
    'ish eloni joylash',
    # community (murojaat / ovoz)
    'murojaat', 'shikoyat', 'ariza yoz', 'ovoz ber', 'ovoz beraman',
]
# «Qanday bron qilaman» kabi HOW-TO savol — bu AMAL emas, ma'lumot so'rovi.
# Gate'ga tushmasin: KB/FAQ javob bersin, «qanday joy bron qilaman» agentга ketmasin.
HOWTO_WORDS = ['qanday', 'qanaqa', 'qandoq', 'qay tarz', 'how']


def is_action_intent(message):
    """Harakat (amal) niyatimi — bron/buyurtma/yozib qo'y/soch oldir.

    HOW-TO savol («qanday bron qilaman») — amal EMAS, False qaytaradi.
    `service.build_response` va `handle()` shu bo'yicha agentga chekinadi.
    """
    qn = _norm(message)
    return _contains_any(qn, ACTION_INTENT_WORDS) and not _contains_any(qn, HOWTO_WORDS)


# Mahalla (community) bo'limi — engine'да alohida branch yo'q, KB yoki fallback'ga
# tushadi. Bu so'rovlar agent (community) tomonidан hal qilinsin.
_COMMUNITY_WORDS = ['murojaat', 'shikoyat', 'so rovnoma', 'sorovnoma',
                    'ovoz ber', 'ovoz berish', 'obodonlashtir', 'raisga',
                    'hokimga', 'mahalla xabar']


def is_community_query(message):
    """Mahalla xizmatlari so'rovimi — murojaat, so'rovnoma, mahalla e'lonlari."""
    qn = _norm(message)
    if _contains_any(qn, _COMMUNITY_WORDS):
        return True
    # «mahalla e'lonlari», «mahallamdagi xabarlar»
    if 'mahalla' in qn and ('elon' in qn or 'xabar' in qn or 'yangilik' in qn):
        return True
    return False


# account (o'z profilи/tarixи) — engine'да branch yo'q, ba'zилари KB/FAQ'ga
# tushib agentні soya qiladi (masalan «profilим» → faq). Bularни agent (account)
# hal qilsin.
_ACCOUNT_WORDS = ['buyurtmalarim', 'buyurtmalarimni', 'bronlarim', 'bronlarimni',
                  'safarlarim', 'safarlarimni', 'elonlarim', 'elonlarimni',
                  'profilim', 'profilimni', 'mening profilim',
                  'ismimni', 'ismni ozgartir', 'ismni uzgartir']


def is_account_query(message):
    """O'z profilи/tarixи so'rovimi — buyurtmalarим, bronlarим, profilим, ism o'zgart."""
    qn = _norm(message)
    return _contains_any(qn, _ACCOUNT_WORDS)
POPULAR_WORDS = ['mashhur', 'ommabop', 'eng yaxshi joy', 'top joy', 'nima korsam',
                 'korsa arzigulik', 'reyting baland', 'yaxshi joylar', 'zor joylar',
                 'qiziqarli joy', 'mashxur']
GREET_WORDS = ['salom', 'assalom', 'hormang', 'privet', 'привет', 'здравств',
               'hello', 'hayrli']
HELP_WORDS = ['yordam', 'nima qila ol', 'nima qila bil', 'qanday ishlay',
              'kimsan', 'nimasan', 'help', 'помощь', 'что умеешь', 'imkoniyat',
              'nimalar bor', 'qanday bolim', 'qanaqa bolim', 'bolimlar', 'funksiya',
              'xizmatlar nima', 'sayt nima', 'sayt haqida', 'qanday xizmat',
              'nima ish qila', 'menyu', 'komandalar']

# ── Oddiy muloqot (small talk) — "tushunmadim" demaslik uchun ─────────────────
THANKS_WORDS = ['rahmat', 'raxmat', 'tashakkur', 'спасибо', 'thanks', 'thank you',
                'minnatdor', 'raxmat katta']
BYE_WORDS = ['xayr', 'salomat boling', 'до свидания', 'bye', 'goodbye', 'ketdim']
YESNO_WORDS = {'ha', 'yoq', 'yop', 'ok', 'okey', 'xop', 'mayli', 'da', 'нет', 'да',
               'yes', 'no', 'yaxshi', 'zor', 'boldi'}

# ── Aqlli filtrlar uchun belgilar ─────────────────────────────────────────────
OPEN_WORDS = ['ochiq', 'hozir ochiq', 'ishlayapti', 'ishlayotgan', 'open', 'открыт',
              'работает']
H24_WORDS = ['24 soat', '24soat', '24/7', 'kechasi', 'tungi', 'tunda', 'kruglosutochn',
             'круглосуточ', 'kecha-kunduz']

_NUM_WORDS = {
    'bir': 1, 'bitta': 1, 'ikki': 2, 'ikkita': 2, 'uch': 3, 'uchta': 3,
    'tort': 4, 'tortta': 4, 'besh': 5, 'beshta': 5, 'olti': 6, 'oltita': 6,
    'yetti': 7, 'yettita': 7, 'sakkiz': 8, 'sakkizta': 8, 'toqqiz': 9,
    'toqqizta': 9, 'on': 10, 'onta': 10,
}
_NUM_RE = re.compile(r'\b(' + '|'.join(sorted(_NUM_WORDS, key=len, reverse=True)) + r')\b')

# ── Follow-up (oldingi natija haqida) ─────────────────────────────────────────
FOLLOWUP_FIELDS = {
    'phone':   ['telefon', 'raqam', 'nomer', 'номер', 'phone', 'qongiroq', 'tel raqam'],
    'address': ['manzil', 'address', 'адрес', 'qayerda joylash', 'joylashgan', 'qayerda u'],
    'hours':   ['ish vaqti', 'soat', 'qachon ochiq', 'ochiladi', 'yopiladi', 'ish vaqt', 'часы'],
    'route':   ['yonalish', 'qanday boraman', 'qanday yetib', 'marshrut', 'yol korsat'],
    'detail':  ['haqida', 'batafsil', 'malumot', 'tafsilot', 'korsat u'],
}
_ORDINALS = [('oxirgi', -1), ('eng oxirgi', -1), ('birinchi', 0), ('1chi', 0),
             ('ikkinchi', 1), ('2chi', 1), ('uchinchi', 2), ('3chi', 2),
             ('tortinchi', 3), ('beshinchi', 4)]


def _is_24h(hours):
    """Ish vaqti 24 soatlik ekanini aniqlaydi."""
    if not hours:
        return False
    low = hours.lower()
    return '24/7' in low or ('24' in low and ('soat' in low or 'kun' in low or '/7' in low))


def _parse_quantity(qn):
    """So'rovdagi son: "3 ta", "beshta", "nechta". Standart 4, eng ko'pi 10."""
    m = re.search(r'(\d+)\s*ta', qn)
    if m:
        return max(1, min(10, int(m.group(1))))
    if 'nechta' in qn or 'barcha' in qn or 'hamma' in qn or 'royxat' in qn:
        return 10
    mm = _NUM_RE.search(qn)
    if mm:
        return min(10, _NUM_WORDS[mm.group(1)])
    return 4


def _is_followup(qn):
    if any(_norm(o[0]) in qn for o in _ORDINALS):
        return True
    for ws in FOLLOWUP_FIELDS.values():
        if any(_norm(w) in qn for w in ws):
            return True
    return False


def _followup(qn, last_cards):
    """Oldingi natijalardan biri haqida savolga javob (telefon/manzil/ish vaqti…)."""
    if not last_cards:
        return None
    idx = 0
    for word, i in _ORDINALS:
        if _norm(word) in qn:
            idx = i
            break
    n = len(last_cards)
    if idx < 0:
        idx = n - 1
    if idx >= n:
        idx = 0
    card = last_cards[idx]

    fields = [f for f, ws in FOLLOWUP_FIELDS.items()
              if any(_norm(w) in qn for w in ws)]
    title = card.get('title', 'Joy')
    lines = []
    if 'phone' in fields:
        lines.append(f"📞 Telefon: {card.get('phone') or 'ko‘rsatilmagan'}")
    if 'address' in fields:
        lines.append(f"📍 Manzil: {card.get('subtitle') or 'ko‘rsatilmagan'}")
    if 'hours' in fields:
        lines.append(f"🕒 Ish vaqti: {card.get('hours') or 'ko‘rsatilmagan'}")
    if not lines:  # route / detail / umumiy
        if card.get('subtitle'):
            lines.append(f"📍 {card['subtitle']}")
        if card.get('phone'):
            lines.append(f"📞 {card['phone']}")
        if card.get('hours'):
            lines.append(f"🕒 {card['hours']}")
        if card.get('distance'):
            lines.append(f"📏 Masofa: {card['distance']}")
    reply = f"«{title}»\n" + "\n".join(lines)
    return {'intent': 'followup', 'reply': reply, 'cards': [card],
            'actions': [], 'used_center': False, 'category': None, 'next_offset': 0}


# ── "Balki buni nazarda tutdingizmi?" — fuzzy taklif indeksi ─────────────────
# (term, ko'rsatiladigan_yorliq, yuboriladigan_savol). Toifalardan darhol,
# bilimlar bazasidan esa birinchi chaqiruvda (aylanma importdan qochish) to'ladi.
_SUGGEST_TERMS = []
for _cat, _words in CATEGORY_KEYWORDS.items():
    _lbl = CATEGORY_LABEL.get(_cat, (_cat, ''))[0]
    _q = f'eng yaqin {_lbl.lower()}'
    for _w in _words:
        for _part in _norm(_w).split():
            if len(_part) >= 4:
                _SUGGEST_TERMS.append((_part, f'Eng yaqin {_lbl.lower()}', _q))
_KB_TERMS_LOADED = False


def _ensure_kb_terms():
    global _KB_TERMS_LOADED
    if _KB_TERMS_LOADED:
        return
    from . import knowledge
    for e in knowledge.KB:
        q = e['keywords'][0]
        for k in e['keywords']:
            for part in _norm(k).split():
                if len(part) >= 4:
                    _SUGGEST_TERMS.append((part, e['title'], q))
    _KB_TERMS_LOADED = True


def suggest(qn):
    """Tushunilmagan matnga eng yaqin ma'lum mavzuni fuzzy topadi (yoki None).

    "aptekaa", "taksii", "dorexona" kabi xato/yaqin so'zlarni ushlaydi va
    foydalanuvchiga "balki shuni demoqchimisiz?" deb taklif qilish uchun ishlatiladi.
    """
    _ensure_kb_terms()
    tokens = [t for t in re.findall(r"[a-zа-яё]+", qn) if len(t) >= 3]
    best, best_ratio = None, 0.0
    for tok in tokens:
        for term, label, q in _SUGGEST_TERMS:
            r = difflib.SequenceMatcher(None, tok, term).ratio()
            if r > best_ratio and r >= 0.78:
                best_ratio, best = r, (label, q)
    return {'label': best[0], 'q': best[1]} if best else None


def fallback(message):
    """LLM o'chiq/ishlamaganda — boshi berk ko'cha o'rniga foydali javob.

    views.py chaqiradi. Yaqin mavzu topilsa "balki shuni demoqchimisiz?" taklifini,
    aks holda umumiy bo'limlar tugmalarini qaytaradi — har doim yo'naltiradi.
    """
    from . import knowledge
    qn = _norm(message)
    sug = suggest(qn)
    actions = knowledge.overview_actions()
    if sug:
        reply = (f"Buni to'liq tushunmadim. 🤔 Balki «{sug['label']}» demoqchimisiz? "
                 f"Yoki quyidagilardan tanlang:")
        actions = [{'label': f"👉 {sug['label']}", 'q': sug['q']}] + actions
    else:
        reply = ("Buni tushunmadim. 😊 Lekin men eng yaqin joyni topish, e'lon, taksi, "
                 "do'kon, to'lov va boshqalarda yordam beraman. Quyidagilardan birini "
                 "tanlang yoki savolingizni boshqacharoq yozing:")
    return {'reply': reply, 'actions': actions}

# Fuzzy moslash uchun bir so'zli kalitlarning tekis ro'yxati (cat bilan)
_FUZZY_INDEX = []
for _cat, _words in CATEGORY_KEYWORDS.items():
    for _w in _words:
        _wn = _norm(_w)
        if ' ' not in _wn and len(_wn) >= 4:
            _FUZZY_INDEX.append((_wn, _cat))


def detect_category(qn):
    """Toifani aniqlaydi: avval aniq moslik (eng uzun yutadi), keyin fuzzy.

    Fuzzy bosqichi "dorxona", "aptaka", "shofoxona" kabi xatolarni ham ushlaydi.
    """
    # 1) Aniq substring moslik — eng uzun kalit yutadi ("tez yordam" > "yordam")
    best, best_len = None, 0
    for cat, words in CATEGORY_KEYWORDS.items():
        for w in words:
            wn = _norm(w)
            if wn and wn in qn and len(wn) > best_len:
                best, best_len = cat, len(wn)
    if best:
        return best

    # 2) Fuzzy — matndagi har bir so'zni kalitlar bilan taqqoslash
    tokens = [t for t in re.findall(r"[a-zа-яё]+", qn) if len(t) >= 4]
    best_ratio = 0.0
    for tok in tokens:
        for wn, cat in _FUZZY_INDEX:
            r = difflib.SequenceMatcher(None, tok, wn).ratio()
            if r > best_ratio and r >= 0.8:
                best_ratio, best = r, cat
    return best


def _contains_any(qn, words):
    return any(_norm(w) in qn for w in words)


def _has_location(loc):
    return isinstance(loc, (tuple, list)) and len(loc) == 2 and \
        loc[0] is not None and loc[1] is not None


# ─── Ish vaqti tahlili: hozir ochiqmi? ────────────────────────────────────────
_HOURS_RE = re.compile(r'(\d{1,2})[:.](\d{2})\s*[-–—to]{1,2}\s*(\d{1,2})[:.](\d{2})')


def _is_open_now(hours):
    """Ish vaqti matnidan hozir ochiqligini aniqlaydi. Aniqlab bo'lmasa None."""
    if not hours:
        return None
    low = hours.lower()
    if '24' in low and ('soat' in low or '/7' in low or 'kun' in low):
        return True
    m = _HOURS_RE.search(hours)
    if not m:
        return None
    try:
        from django.utils import timezone
        now = timezone.localtime()
    except Exception:
        return None
    cur = now.hour * 60 + now.minute
    o = int(m.group(1)) % 24 * 60 + int(m.group(2))
    c = int(m.group(3)) % 24 * 60 + int(m.group(4))
    if c <= o:  # tunda yopiladigan (masalan 22:00–06:00)
        return cur >= o or cur < c
    return o <= cur < c


def _route_url(lat, lng):
    """Universal yo'nalish havolasi (mobil qurilmada native xaritani ochadi)."""
    return f'https://www.google.com/maps/dir/?api=1&destination={lat},{lng}'


def _place_card(place, dist_km=None):
    """Place obyektidan boy widget kartasi."""
    from django.urls import reverse
    label, emoji = CATEGORY_LABEL.get(place.category, ('Joy', '📍'))
    card = {
        'title': place.localized_name,
        'subtitle': place.address or label,
        'icon': emoji,
        'category': label,
        'lat': place.latitude, 'lng': place.longitude,
        'url': reverse('places:place_detail', args=[place.pk]),
        'route_url': _route_url(place.latitude, place.longitude),
        'phone': place.phone or '',
        'hours': place.working_hours or '',
    }
    if dist_km is not None:
        card['distance'] = _fmt_dist(dist_km)
        card['walk'] = f'🚶 ~{_walk_min(dist_km)} daq'
    card['open'] = _is_open_now(place.working_hours)
    try:
        if place.review_count:
            card['rating'] = place.avg_rating
            card['reviews'] = place.review_count
    except Exception:
        pass
    return card


def _store_card(store, dist_km=None):
    """Delivery do'koni kartasi."""
    from django.urls import reverse
    card = {
        'title': store.name,
        'subtitle': store.address or "Do'kon",
        'icon': '🛒', 'category': "Do'kon",
        'lat': store.latitude, 'lng': store.longitude,
        'url': reverse('delivery:store_detail', args=[store.pk]),
        'route_url': _route_url(store.latitude, store.longitude),
        'phone': store.phone or '',
        'hours': getattr(store, 'working_hours', '') or '',
    }
    if dist_km is not None:
        card['distance'] = _fmt_dist(dist_km)
        card['walk'] = f'🚶 ~{_walk_min(dist_km)} daq'
    card['open'] = _is_open_now(getattr(store, 'working_hours', ''))
    return card


def _nearest_places(category, lat, lng, limit=4, offset=0, open_now=False, h24=False):
    from places.models import Place
    qs = Place.objects.filter(is_active=True, category=category)
    scored = sorted(
        ((p, _haversine(lat, lng, p.latitude, p.longitude)) for p in qs),
        key=lambda x: x[1],
    )
    if open_now:
        scored = [x for x in scored if _is_open_now(x[0].working_hours) is True]
    if h24:
        scored = [x for x in scored if _is_24h(x[0].working_hours)]
    return scored[offset:offset + limit]


def _popular_places(limit=5):
    """Eng ko'p ko'rilgan faol joylar (joylashuvsiz — umumiy mashhurlik)."""
    from places.models import Place
    return list(Place.objects.filter(is_active=True).order_by('-views', 'name')[:limit])


# ── Real ma'lumot qidiruvi (e'lon, ish, to'yxona) ─────────────────────────────
# Qidiruv so'zini ajratishda tashlab yuboriladigan (stop) so'zlar: intent fe'llari
# va umumiy yordamchi so'zlar. Qolgan mazmunli so'zlar bo'yicha bazadan qidiriladi.
_STOPWORDS = frozenset("""
menga meni men eng yaqin kerak kerakmi bor yoq qanday qanaqa topib top ber bering
korsat uchun bilan haqida mavjud bormi nechta narx arzon qimmat yangi eski
va yoki hamda bu shu ushbu men sen biz ular sizda menda kim nima qayerda qachon
sotib olaman sotaman sotmoqchiman sotmoqchi sotuv sotiladi ijara ijaraga beraman
elon elonlar reklama ish ishla ishchi ishlash ishga joylash vakansiya rezyume
bron band qil qilish qiladi qilsam qilmoqchiman qilaman joy joylar zal boladi bolsa
mumkin izlayapman qidiryapman qidiryabman kk
""".split())


def _search_terms(message):
    qn = _norm(message)
    return [w for w in re.findall(r"[a-zа-яё0-9]+", qn)
            if len(w) >= 3 and w not in _STOPWORDS]


def _icontains_q(terms, fields):
    """Har bir so'z bo'yicha (title/description/…) OR icontains filtri."""
    from django.db.models import Q
    q = Q()
    for t in terms:
        sub = Q()
        for f in fields:
            sub |= Q(**{f + '__icontains': t})
        q |= sub
    return q


def _som(v):
    return f"{v:,}".replace(',', ' ') + " so'm"


def _search_ads(message, limit=5):
    from main.models import Ad
    terms = _search_terms(message)
    qs = Ad.objects.filter(status='active')
    if terms:
        qs = qs.filter(_icontains_q(terms, ['title', 'description', 'location']))
    return list(qs.order_by('-is_boosted', '-created_at')[:limit])


def _search_jobs(message, limit=5):
    from main.models import JobAd
    terms = _search_terms(message)
    qs = JobAd.objects.filter(status='active')
    if terms:
        qs = qs.filter(_icontains_q(terms, ['title', 'company', 'description']))
    return list(qs.order_by('-created_at')[:limit])


def _search_venues(message, limit=5):
    from booking.models import Venue
    terms = _search_terms(message)
    qs = Venue.objects.filter(is_active=True)
    if terms:
        qs = qs.filter(_icontains_q(terms, ['name', 'address', 'description']))
    return list(qs.order_by('-created_at')[:limit])


def _ad_card(ad):
    from django.urls import reverse
    if ad.price_type == 'free':
        price = 'Bepul'
    elif ad.price:
        price = _som(ad.price)
    else:
        price = ''
    loc = ad.location or ad.get_category_display()
    subtitle = ' · '.join([p for p in (price, loc) if p])
    card = {'title': ad.title, 'subtitle': subtitle or ad.get_category_display(),
            'icon': '🏷️', 'url': reverse('ad_detail', args=[ad.pk]),
            'phone': ad.contact_phone or ''}
    if ad.latitude and ad.longitude:
        card['route_url'] = _route_url(ad.latitude, ad.longitude)
    return card


def _job_card(job):
    from django.urls import reverse
    sal = ''
    if job.salary_min and job.salary_max:
        sal = f'{_som(job.salary_min)}–{_som(job.salary_max)}'
    elif job.salary_min:
        sal = f'{_som(job.salary_min)} dan'
    parts = [job.company, sal, job.location]
    subtitle = ' · '.join([p for p in parts if p])
    return {'title': job.title, 'subtitle': subtitle or job.company,
            'icon': '💼', 'url': reverse('job_detail', args=[job.pk]),
            'phone': job.contact_phone or ''}


def _venue_card(v):
    from django.urls import reverse
    price = (_som(v.price_per_day) + '/kun') if v.price_per_day else ''
    cap = f'{v.capacity} kishi' if v.capacity else ''
    parts = [v.get_venue_type_display(), price, cap]
    subtitle = ' · '.join([p for p in parts if p])
    card = {'title': v.name, 'subtitle': subtitle or (v.address or 'Joy'),
            'icon': '🏛️', 'url': reverse('venue_detail', args=[v.pk]),
            'phone': v.phone or ''}
    if v.latitude and v.longitude:
        card['route_url'] = _route_url(v.latitude, v.longitude)
    return card


def _nearest_stores(lat, lng, limit=4, offset=0):
    from delivery.models import Store
    qs = Store.objects.filter(is_active=True, latitude__isnull=False,
                              longitude__isnull=False)
    scored = sorted(
        ((s, _haversine(lat, lng, s.latitude, s.longitude)) for s in qs),
        key=lambda x: x[1],
    )
    return scored[offset:offset + limit]


def _resolve_point(location, result):
    """Foydalanuvchi nuqtasi: joylashuv bo'lsa — o'sha, bo'lmasa markaz."""
    if _has_location(location):
        return location[0], location[1]
    result['used_center'] = True
    return CENTER


def handle(message, location=None, context=None):
    """Asosiy kirish nuqtasi.

    message  — foydalanuvchi matni.
    location — (lat, lng) yoki None (widget geolokatsiya bergan bo'lsa).
    context  — {last_category, offset} (klient suhbatni davom ettirish uchun yuboradi).

    Qaytaradi: dict {intent, reply, cards, actions, used_center, category, next_offset}.
    """
    from django.urls import reverse

    context = context or {}
    qn = _norm(message)
    result = {'intent': 'unknown', 'reply': '', 'cards': [], 'actions': [],
              'used_center': False, 'category': None, 'next_offset': 0}

    if not qn:
        result.update(intent='empty',
                      reply="Savolingizni yozing — masalan: «Menga eng yaqin dorixonani ko'rsat».")
        return result

    # ── HARAKAT NIYATI → engine CHEKINADI (agent hal qiladi) ──────────────────
    # «bron qil», «buyurtma qil», «soch oldir» — category (barber/restaurant) yoki
    # delivery/booking branchи ushlab, agentни soya qilmasin. intent='unknown'
    # qoladi → service.build_response agentга uzatadi. «eng yaqin sartaroshxona»
    # (harakatsiz) o'zgarmaydi; «qanday bron qilaman» (HOW-TO) KB'ga o'tadi.
    # Taksi ARXIVLANGAN — «taksi chaqir», «taksi kerak» kabi AMAL so'rovlari
    # agentga chekinmasin (agentda ham taxi tool yo'q). Foydalanuvchiga xizmat
    # yopiqligi darhol aytiladi — mavhum «tushunmadim» javobi o'rniga.
    if not settings.TAXI_ENABLED and _contains_any(qn, TAXI_WORDS):
        from . import knowledge
        result.update(
            intent='taxi_disabled',
            reply=("🚧 Taksi xizmati hozircha o'chirilgan. Yetkazib berish, joy "
                   "bron qilish va boshqa bo'limlar ishlayapti — nima kerakligini "
                   "yozing, yordam beraman."),
            actions=knowledge.overview_actions(),
        )
        return result

    if is_action_intent(message):
        return result

    category = detect_category(qn)
    is_continue = _contains_any(qn, CONTINUE_WORDS)
    offset = 0
    last_cards = context.get('last_cards')
    if not isinstance(last_cards, list):
        last_cards = None

    # ── 0.5) FOLLOW-UP: oldingi natija haqida ("birinchisining telefoni", "manzili") ─
    if not category and not is_continue and last_cards and _is_followup(qn):
        fr = _followup(qn, last_cards)
        if fr:
            return fr

    # Suhbatni davom ettirish: "yana" desa oldingi toifani offset bilan davom ettiramiz
    if not category and is_continue and context.get('last_category') in VALID_CATEGORIES:
        category = context['last_category']
        try:
            offset = max(0, int(context.get('offset') or 0))
        except (TypeError, ValueError):
            offset = 0

    # ── 1) JOY TOPISH (eng yaqin dorixona/shifoxona/bank...) ──────────────────
    if category:
        label, emoji = CATEGORY_LABEL.get(category, ('Joy', '📍'))
        lat, lng = _resolve_point(location, result)

        # Aqlli filtrlar: "N ta", "hozir ochiq", "24 soat"
        limit = _parse_quantity(qn)
        open_now = _contains_any(qn, OPEN_WORDS)
        h24 = _contains_any(qn, H24_WORDS)
        pairs = _nearest_places(category, lat, lng, limit=limit, offset=offset,
                                open_now=open_now, h24=h24)

        result['category'] = category
        result['intent'] = 'nearest_place'
        result['next_offset'] = offset + len(pairs)

        # Qo'llanilgan filtrni tavsiflovchi so'z
        flt = ''
        if open_now:
            flt = 'hozir ochiq '
        elif h24:
            flt = '24 soat ishlaydigan '

        if pairs:
            result['cards'] = [_place_card(p, d) for p, d in pairs]
            if offset > 0:
                result['reply'] = f"{emoji} Mana yana {flt}{label.lower()}lar:"
            else:
                p0, d0 = pairs[0]
                where = ('sizga' if not result['used_center'] else 'shahar markaziga')
                result['reply'] = (
                    f"{emoji} Eng yaqin {flt}{label.lower()} — «{p0.localized_name}», "
                    f"{where} {_fmt_dist(d0)} ({_walk_min(d0)} daq piyoda, "
                    f"{_drive_min(d0)} daq mashinada)."
                )
                if len(pairs) > 1:
                    result['reply'] += " Boshqa variantlar quyida:"
                if result['used_center']:
                    result['reply'] += ("\n\n📍 Aniq natija uchun pastdagi 📍 tugmasi "
                                        "bilan joylashuvingizni ulang.")
        else:
            if offset > 0:
                result['reply'] = f"Boshqa {flt}{label.lower()} qolmadi. 🙂"
            elif open_now:
                result['reply'] = (f"Hozir ochiq {label.lower()} topilmadi (ish vaqti "
                                   f"ma'lum bo'lganlar orasida). Barchasini xaritadan ko'ring.")
            elif h24:
                result['reply'] = (f"24 soat ishlaydigan {label.lower()} topilmadi. "
                                   f"Barcha {label.lower()}larni xaritadan ko'ring.")
            else:
                result['reply'] = (f"Kechirasiz, hozircha bazada {label.lower()} "
                                   f"topilmadi. Xaritadan ko'rib chiqing.")
        result['actions'] = [
            {'label': f'🗺 Xaritada {label.lower()}',
             'url': reverse('places:place_list') + f'?category={category}'},
        ]
        if result['next_offset'] and len(pairs) == limit and limit <= 4:
            result['actions'].insert(0, {'label': f'➕ Yana {label.lower()}',
                                         'q': f'yana {label.lower()}'})
        return result

    # ── 1.3) MASHHUR JOYLAR ("mashhur joylar", "nima ko'rsam bo'ladi") ────────
    if _contains_any(qn, POPULAR_WORDS):
        places = _popular_places()
        if places:
            result['cards'] = [_place_card(p) for p in places]
            result['reply'] = "⭐ Eng mashhur joylar (ko'p ko'rilgan):"
        else:
            result['reply'] = "Hozircha mashhur joylar ro'yxati bo'sh. Xaritani ko'ring."
        result['intent'] = 'popular'
        result['actions'] = [
            {'label': '🗺 Xarita', 'url': reverse('places:map')},
            {'label': '🏞 Sayohat', 'url': reverse('places:tourism_list')},
        ]
        return result

    # ── 1.5) SAYT FUNKSIYALARI BO'YICHA QO'LLANMA (bilimlar bazasi) ──────────
    # "e'lon qanday joylayman", "do'kon ochish", "kommunal to'lov" kabi savollar.
    # Joy topishdan keyin, umumiy xizmat yorliqlaridan oldin tekshiriladi.
    from . import knowledge
    # Taksi arxivlangan bo'lsa `knowledge.answer()` taksi yozuvlarini o'zi
    # chetlab o'tadi (TAXI_KB_IDS) — bu yerda qo'shimcha filtr kerak emas.
    kb = knowledge.answer(qn)
    if kb:
        actions = []
        for label, urlname in kb.get('actions', []):
            try:
                actions.append({'label': label, 'url': reverse(urlname)})
            except Exception:
                pass  # url topilmasa — o'sha havolani jimgina tashlab ketamiz
        result.update(intent='faq', reply=kb['answer'], actions=actions)
        result['kb_id'] = kb['id']
        return result

    # ── 2) TAKSI ──────────────────────────────────────────────────────────────
    # Taksi arxivlangan bo'lsa bu yergacha yetib kelmaydi — yuqoridagi
    # TAXI_ENABLED tekshiruvi barcha taksi so'rovlarini ushlab qoladi.
    if _contains_any(qn, TAXI_WORDS):
        result.update(
            intent='taxi',
            reply=("🚗 Taksi chaqirish yoki taksistlarni ko'rish uchun taksi "
                   "bo'limiga o'ting — narxni hisoblash va onlayn haydovchilarni "
                   "topishingiz mumkin."),
            actions=[
                {'label': '🚕 Taksi chaqirish', 'url': reverse('taxi:home')},
                {'label': '🗺 Xaritada taksistlar', 'url': reverse('taxi:map')},
            ],
        )
        return result

    # ── 3) YETKAZIB BERISH / DO'KONLAR (eng yaqin do'konni ham topadi) ────────
    if _contains_any(qn, DELIVERY_WORDS):
        result['intent'] = 'delivery'
        wants_near = _contains_any(qn, NEAR_WORDS) or 'dokon' in qn or 'магазин' in qn
        if wants_near:
            lat, lng = _resolve_point(location, result)
            pairs = _nearest_stores(lat, lng, limit=4)
            if pairs:
                result['cards'] = [_store_card(s, d) for s, d in pairs]
                s0, d0 = pairs[0]
                where = ('sizga' if not result['used_center'] else 'markazga')
                result['reply'] = (f"🛒 Eng yaqin do'kon — «{s0.name}», {where} "
                                   f"{_fmt_dist(d0)}. Variantlar quyida:")
                if result['used_center']:
                    result['reply'] += "\n\n📍 Aniqlik uchun joylashuvni ulang."
        if not result['cards']:
            result['reply'] = ("🛒 Do'konlar va yetkazib berish bo'limida oziq-ovqat "
                               "va boshqa mahsulotlarni topishingiz mumkin.")
        result['actions'] = [{'label': "🏪 Barcha do'konlar",
                              'url': reverse('delivery:store_list')}]
        return result

    # ── 4) E'LONLAR (marketplace) — real e'lonlarni qidiradi ─────────────────
    if _contains_any(qn, ADS_WORDS):
        from urllib.parse import urlencode
        q = message.strip()
        ads = _search_ads(message)
        result['intent'] = 'ads'
        if ads:
            result['cards'] = [_ad_card(a) for a in ads]
            result['reply'] = "🏷️ Mana shu bo'yicha e'lonlar:"
        else:
            result['reply'] = ("Bu bo'yicha e'lon topilmadi. Barcha e'lonlarni ko'ring "
                               "yoki boshqacharoq qidiring:")
        result['actions'] = [
            {'label': f"🔎 «{q[:24]}» qidirish",
             'url': reverse('global_search') + '?' + urlencode({'q': q})},
            {'label': "📋 Barcha e'lonlar", 'url': reverse('all_ads')},
        ]
        return result

    # ── 5) ISH / VAKANSIYA — real ish e'lonlarini qidiradi ───────────────────
    if _contains_any(qn, JOB_WORDS):
        jobs = _search_jobs(message)
        result['intent'] = 'jobs'
        if jobs:
            result['cards'] = [_job_card(j) for j in jobs]
            result['reply'] = "💼 Mos ish o'rinlari:"
        else:
            result['reply'] = ("Bu bo'yicha ish e'loni topilmadi. Barcha vakansiyalarni ko'ring:")
        result['actions'] = [
            {'label': "💼 Ish e'lonlari", 'url': reverse('job_list')},
            {'label': '📄 Rezyumelar', 'url': reverse('resume_list')},
        ]
        return result

    # ── 6) BRON (booking) — real to'yxona/zallarni qidiradi ──────────────────
    if _contains_any(qn, BOOKING_WORDS):
        venues = _search_venues(message)
        result['intent'] = 'booking'
        if venues:
            result['cards'] = [_venue_card(v) for v in venues]
            result['reply'] = "📅 Bron qilish mumkin bo'lgan joylar:"
        else:
            result['reply'] = ("Hozircha mos joy topilmadi. Barcha joylarni ko'ring:")
        result['actions'] = [{'label': '📅 Barcha joylar', 'url': reverse('venue_list')}]
        return result

    # ── 6.5) ODDIY MULOQOT (rahmat / xayr / ha-yo'q) — "tushunmadim" demaslik ──
    if _contains_any(qn, THANKS_WORDS):
        result.update(intent='smalltalk',
                      reply="Arzimaydi! 😊 Yana biror narsa kerak bo'lsa, bemalol yozing.")
        return result
    if _contains_any(qn, BYE_WORDS):
        result.update(intent='smalltalk',
                      reply="Xayr, sog' bo'ling! 👋 Yana savolingiz bo'lsa, shu yerdaman.")
        return result
    if qn in YESNO_WORDS or qn.split() and all(w in YESNO_WORDS for w in qn.split()):
        from . import knowledge
        result.update(
            intent='smalltalk',
            reply=("Yaxshi! 👍 Nima bilan yordam beray? Masalan «eng yaqin dorixona» "
                   "yoki «e'lon qanday joylayman». Bo'limlardan birini tanlang:"),
            actions=knowledge.overview_actions())
        return result

    # ── 7) SALOMLASHISH ───────────────────────────────────────────────────────
    if _contains_any(qn, GREET_WORDS):
        result.update(
            intent='greeting',
            reply=("Assalomu alaykum! 👋 Men SamCity yordamchisiman. Eng yaqin "
                   "dorixona, shifoxona, bank yoki restoranni topib beraman, "
                   "taksi, do'kon va e'lonlar bo'yicha yordam beraman. Nima kerak?"),
        )
        return result

    # ── 8) YORDAM / SAYT IMKONIYATLARI SHARHI ─────────────────────────────────
    if _contains_any(qn, HELP_WORDS):
        from . import knowledge
        result.update(
            intent='help',
            reply=("Men SamCity'ning barcha bo'limlari bo'yicha yordam bera olaman 👇\n\n"
                   "• 📍 Eng yaqin joyni topish (dorixona, shifoxona, bank, restoran…)\n"
                   "• 📢 E'lon joylash, qidirish, ko'tarish\n"
                   "• 💼 Ish e'lonlari va rezyumelar\n"
                   "• 🚕 Taksi chaqirish yoki taksist bo'lish\n"
                   "• 🛒 Do'kondan buyurtma yoki o'z do'koningizni ochish\n"
                   "• 📅 To'yxona/zal bron qilish\n"
                   "• 💳 Kommunal va boshqa to'lovlar (Payme/Click)\n"
                   "• 🏘️ Mahalla: e'lonlar, so'rovnomalar, murojaat, yordam markazi\n"
                   "• 🗺️ Xarita, sayohat va joy qo'shish\n"
                   "• 👤 Ro'yxatdan o'tish, profil, bildirishnomalar, mobil ilova\n\n"
                   "Biror bo'limni tanlang yoki savolingizni yozing:"),
            actions=knowledge.overview_actions(),
        )
        return result

    # ── Tushunilmadi → LLM fallback uchun 'unknown' ───────────────────────────
    return result
