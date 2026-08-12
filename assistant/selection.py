"""Ovoz bilan tanlashni yechish — «anorni», «ikkinchisini», «eng arzonini».

Ekranga ro'yxat chiqarilgach (SelectionSet), foydalanuvchi tanlovini KO'P HOLDA
LLM'SIZ (~10 ms) aniqlaymiz. Amalda tanlovlarning ~85% i 1-4 bosqichda hal bo'ladi;
qolganigina agent LLM ga qisqa ro'yxat yuboradi.

Bosqichlar (shu tartibda):
  1. Tartib raqami — «birinchi», «2-chi», «oxirgi»
  2. Nomga to'g'ridan-to'g'ri moslik — `aliases` ichida
  3. Fuzzy moslik — «anur», «anorchi» (difflib, chegara ~0.75)
  4. Ustunlik — «eng arzoni», «eng yaqini», «eng yaxshi reytingli»
  5. Topilmasa → None (agent LLM ga qisqa ro'yxat yuboradi)

`engine._norm()` qayta ishlatiladi (apostrof normalizatsiyasi bir xil bo'lsin).
"""

import difflib
import re

from .engine import _norm


FUZZY_THRESHOLD = 0.75

# So'z bilan tartib sonlar (o'zbek). "birinchisini", "ikkinchisi" — substring bilan mos.
_WORD_ORDINALS = {
    'birinchi': 0, 'ikkinchi': 1, 'uchinchi': 2, 'tortinchi': 3, 'beshinchi': 4,
    'oltinchi': 5, 'yettinchi': 6, 'sakkizinchi': 7, 'toqqizinchi': 8, 'oninchi': 9,
}
_LAST_WORDS = ('oxirgi', 'songgi', 'eng oxirgi', 'oxirgisi', 'songgisi')
_NUM_ORDINAL_RE = re.compile(r'(\d+)\s*-?\s*chi')   # "2-chi", "2chi", "2 chi"

# Ustunlik (superlative) kalitlari → (maydon, yo'nalish). direction: min|max
_SUPERLATIVE = [
    (('eng arzon', 'arzonini', 'arzonrog', 'arzon'), ('price', 'min')),
    (('eng qimmat', 'qimmatini', 'qimmat'), ('price', 'max')),
    (('eng yaqin', 'yaqinini', 'yaqinrog'), ('distance', 'min')),
    (('eng uzoq', 'uzogini'), ('distance', 'max')),
    (('eng yaxshi', 'reytingi baland', 'eng zor', 'eng sifatli',
      'yuqori reyting'), ('rating', 'max')),
]


def resolve(ref, utterance):
    """SelectionSet (ref) ichidan foydalanuvchi aytganini topadi. Topilmasa None.

    DB'dan ro'yxatni yuklaydi (muddati o'tgan bo'lsa None) va `resolve_items` ga
    o'tkazadi.
    """
    items = _load_items(ref)
    if items is None:
        return None
    return resolve_items(items, utterance)


def resolve_items(items, utterance):
    """Sof funksiya (DB'siz) — testlar to'g'ridan-to'g'ri chaqiradi.

    items — [{id, index, title, subtitle?, aliases?, price?, distance?, rating?}].
    Qaytaradi: element (dict) yoki None.
    """
    if not items:
        return None
    qn = _norm(utterance)
    if not qn:
        return None

    # 1) Tartib raqami
    idx = _ordinal_index(qn, len(items))
    if idx is not None:
        return items[idx]

    # 2) Nomga to'g'ridan-to'g'ri moslik (eng uzun mos yutadi)
    hit = _by_name(qn, items)
    if hit is not None:
        return hit

    # 3) Fuzzy moslik
    hit = _by_fuzzy(qn, items)
    if hit is not None:
        return hit

    # 4) Ustunlik
    hit = _by_superlative(qn, items)
    if hit is not None:
        return hit

    # 5) Topilmadi
    return None


# ── 1) Tartib raqami ─────────────────────────────────────────────────────────

def _ordinal_index(qn, n):
    if n <= 0:
        return None
    if any(w in qn for w in _LAST_WORDS):
        return n - 1
    for word, i in _WORD_ORDINALS.items():
        if word in qn:
            return i if i < n else None
    m = _NUM_ORDINAL_RE.search(qn)
    if m:
        i = int(m.group(1)) - 1
        if 0 <= i < n:
            return i
    return None


# ── 2) Nomga to'g'ridan-to'g'ri moslik ──────────────────────────────────────

def _aliases_of(item):
    """Element uchun taqqoslash kalitlari: aliases + title (normalizatsiyalangan)."""
    keys = []
    for a in (item.get('aliases') or []):
        an = _norm(a)
        if an:
            keys.append(an)
    tn = _norm(item.get('title', ''))
    if tn:
        keys.append(tn)
    return keys


def _by_name(qn, items):
    best, best_len = None, 0
    for item in items:
        for key in _aliases_of(item):
            # Kalit so'rov ichida bo'lsa (masalan «anorni» → «anor»)
            if len(key) >= 3 and key in qn and len(key) > best_len:
                best, best_len = item, len(key)
    return best


# ── 3) Fuzzy moslik ──────────────────────────────────────────────────────────

def _by_fuzzy(qn, items):
    tokens = [t for t in re.findall(r"[a-zа-яё0-9]+", qn) if len(t) >= 3]
    if not tokens:
        return None
    best, best_ratio = None, 0.0
    for item in items:
        for key in _aliases_of(item):
            for kw in key.split():
                if len(kw) < 3:
                    continue
                for tok in tokens:
                    r = difflib.SequenceMatcher(None, tok, kw).ratio()
                    if r > best_ratio:
                        best_ratio, best = r, item
    return best if best_ratio >= FUZZY_THRESHOLD else None


# ── 4) Ustunlik (eng arzon / yaqin / yaxshi) ─────────────────────────────────

def _by_superlative(qn, items):
    for words, (field, direction) in _SUPERLATIVE:
        if any(w in qn for w in words):
            scored = [(it, _num(it.get(field))) for it in items]
            scored = [(it, v) for it, v in scored if v is not None]
            if not scored:
                return None
            key = min if direction == 'min' else max
            return key(scored, key=lambda x: x[1])[0]
    return None


def _num(v):
    """Qiymatni songa aylantiradi (masalan '1.2 km' → 1.2). Bo'lmasa None."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r'\d+(?:[.,]\d+)?', str(v))
    return float(m.group(0).replace(',', '.')) if m else None


# ── DB yuklash ───────────────────────────────────────────────────────────────

def create(ctx, section, items, task=None):
    """Ekran ro'yxatini SelectionSet sifatida saqlaydi va uni ESLAB QOLADI.

    Tool card_list/product_grid qurishdan oldin shuni chaqiradi. Ro'yxat faol
    `AgentTask.last_ui_ref` ga bog'lanadi — shu tufayli KEYINGI navbatda:
      • `prompts.build_dynamic_context()` ro'yxatni ID'lari bilan modelga beradi
        (busiz model `store_id`/`product_id` ni hech qachon bila olmaydi);
      • foydalanuvchi «ikkinchisini» desa `resolve(ref, ...)` LLM'siz topadi.
    """
    from .models import SelectionSet

    # Ro'yxatni faol vazifaga bog'laymiz (egasi aniq bo'lsa — anonim/sessiyasiz
    # holatda keraksiz yozuv yaratmaymiz).
    if task is None and _has_owner(ctx):
        try:
            from . import task as task_mod
            task = task_mod.get_or_create_active(ctx, goal=section)
        except Exception:
            task = None

    ss = SelectionSet.objects.create(
        user=(ctx.user if (ctx and ctx.is_authenticated) else None),
        session_key=(ctx.session_key if ctx else '') or '',
        task=task, section=section[:24], items=items or [],
    )

    if task is not None:
        try:
            from . import task as task_mod
            task_mod.remember_selection(task, ss.ref)
            # Shu so'rov davomida ham yangi ro'yxat ko'rinsin.
            if ctx is not None:
                ctx.task = task
        except Exception:
            pass
    return ss


def _has_owner(ctx):
    """Vazifa yaratish mumkinmi — foydalanuvchi yoki sessiya kaliti bormi."""
    if ctx is None:
        return False
    return bool(ctx.is_authenticated or getattr(ctx, 'session_key', ''))


# ── Modelga beriladigan ixcham ro'yxat (dinamik kontekst uchun) ──────────────

def identifier_of(item):
    """Element uchun tool'ga beriladigan ID: «store_id=12», «venue_id=abc»...

    ⚠️ Karta `id` maydonида prefiks bor («venue:abc», «store:12») — modelга XOM
    ID (prefikssiz) kerak, aks holда tool «venue:abc» ni pk deб qabul qilib xato
    beradi (jonli bron sinovда aynan shu bo'lgan). Shuning uchun bu yerда aniq
    `*_id` maydonlар beriladi. Bo'lmasa bo'sh satr (`places` — keyingi amal yo'q).
    """
    for key in ('store_id', 'product_id', 'venue_id', 'service_id', 'staff_id',
                'route_id', 'poll_option_id', 'booking_id',
                'ad_id', 'job_id', 'resume_id'):
        if item.get(key) is not None:
            return f'{key}={item[key]}'
    return ''


def describe(items, limit=12):
    """Ro'yxatni model o'qiydigan ixcham qatorlarga aylantiradi.

    ⚠️ Sarlavhalar foydalanuvchi kiritgan matn (do'kon/mahsulot nomi) — ular
    TOZALANADI. Busiz do'kon nomidagi «[SYSTEM: ...]» to'g'ridan-to'g'ri
    system-promptga tushadi va model unga ergashadi (smoke-testda isbotlangan).
    """
    from .sanitize import untrusted

    lines = []
    for it in (items or [])[:limit]:
        ident = identifier_of(it)
        title = untrusted(it.get('title', ''))
        line = f"{it.get('index')}) {title}"
        if ident:
            line += f" — {ident}"
        price = it.get('price')
        if price:
            line += f" — {int(price)} so'm"
        lines.append(line)
    return lines


def load_set(ref):
    """SelectionSet obyektini qaytaradi (muddati o'tgan/yo'q bo'lsa None)."""
    if not ref:
        return None
    try:
        from .models import SelectionSet
        ss = SelectionSet.objects.filter(ref=ref).first()
        if ss is None or ss.is_expired:
            return None
        return ss
    except Exception:
        return None


def _load_items(ref):
    """SelectionSet (ref) elementlarini yuklaydi. Yo'q/muddati o'tgan → None."""
    if not ref:
        return None
    try:
        from .models import SelectionSet
        ss = SelectionSet.objects.filter(ref=ref).first()
        if ss is None or ss.is_expired:
            return None
        return ss.items or []
    except Exception:
        return None
