"""places bo'limi — MANZIL/joy topish (buyurtmasiz). O'qish namunasi.

Bu yerda hech narsa o'zgartirilmaydi (mutating yo'q) — faqat eng yaqin joyni
topib, ekranga chiqaradi. `engine.py` dagi tayyor mantiq (_nearest_places,
masofa/vaqt hisoblari) QAYTA ISHLATILADI — dublikat qilinmaydi.
"""

import os

from .. import engine, selection as sel, ui
from ..registry import tool

# Eng uzoq masofa (km) — bundan narigi joy natijaga tushmaydi. Shofirkon
# ixcham shahar; 83 km natija (boshqa tumandagi) foydasiz. Env bilan sozlanadi.
MAX_PLACE_KM = float(os.environ.get('MAX_PLACE_KM', '20'))


def _user_point(ctx):
    """Foydalanuvchi nuqtasi: joylashuv bo'lsa — o'sha, aks holda shahar markazi."""
    loc = getattr(ctx, 'location', None)
    if (isinstance(loc, (tuple, list)) and len(loc) == 2
            and loc[0] is not None and loc[1] is not None):
        return (loc[0], loc[1]), False
    return engine.CENTER, True


# Kanonik toifalar — yagona manba `engine.CATEGORY_KEYWORDS` kalitlari.
# Sxemadagi `enum` shu ro'yxatni majburlaydi: busiz model o'zbekcha so'z
# («dorixona») uzatib yuborardi — prozadagi ko'rsatma yetarli emas.
CATEGORY_ENUM = sorted(engine.VALID_CATEGORIES)


@tool(
    section='places', action='find_nearest',
    description="Eng yaqin joyning MANZILINI topadi (dorixona, shifoxona, bank, "
                "maktab, davlat idorasi). Faqat «qayerda?» savoliga javob — "
                "bu yerda hech narsa sotib olinmaydi va buyurtma qilinmaydi. "
                "Ovqat/mahsulot olish kerak bo'lsa delivery.find_store ishlating.",
    params={
        'category': ('str', True,
                     "joy toifasi — INGLIZCHA kalit: pharmacy=dorixona, "
                     "hospital=shifoxona, bank=bank/bankomat, restaurant=restoran/kafe, "
                     "wedding=to'yxona, school=maktab, kindergarten=bog'cha",
                     CATEGORY_ENUM),
        'limit': ('int', False, "nechta ko'rsatilsin (standart 4, eng ko'pi 10)"),
        'open_now': ('bool', False, "faqat hozir ochiq joylar"),
    },
)
def find_nearest(ctx, category, limit=4, open_now=False):
    cat = engine.detect_category(engine._norm(category))
    if not cat and category in engine.VALID_CATEGORIES:
        cat = category
    if not cat:
        return {'speech': "Qanaqa joy kerakligini aniqroq ayting — masalan "
                          "«eng yaqin dorixona»."}

    limit = max(1, min(10, int(limit or 4)))
    (lat, lng), used_center = _user_point(ctx)
    # ⚠️ Masofa chegarasi: Place'da tuman maydoni yo'q, shuning uchun tuman
    # filtri o'rniga masofa cap ishlatamiz — 83 km narigi joy chiqmasin.
    # Ko'proq olib, keyin chegaralab qisqartiramiz (yaqinlari yetarli bo'lsin).
    pairs = engine._nearest_places(cat, lat, lng, limit=limit + 6, open_now=bool(open_now))
    pairs = [(p, d) for (p, d) in pairs if d <= MAX_PLACE_KM][:limit]
    label, emoji = engine.CATEGORY_LABEL.get(cat, ('Joy', '📍'))

    if not pairs:
        extra = " (hozir ochiqlari)" if open_now else ""
        return {'speech': f"Yaqin atrofda ({MAX_PLACE_KM} km ichida) "
                          f"{label.lower()}{extra} topilmadi. Xaritadan ko'ring."}

    items = []
    for i, (p, d) in enumerate(pairs, start=1):
        rating = None
        try:
            if p.review_count:
                rating = float(p.avg_rating)
        except Exception:
            rating = None
        items.append({
            'id': f'place:{p.pk}', 'index': i,
            'title': p.localized_name,
            'subtitle': f"{engine._fmt_dist(d)} · 🚶 {engine._walk_min(d)} daq"
                        + (f" · ⭐ {rating}" if rating else ""),
            'aliases': [engine._norm(p.localized_name)],
            'distance': round(d, 3),
            'rating': rating,
        })

    ss = sel.create(ctx, 'places', items)
    tail = "" if not used_center else " (aniqroq natija uchun joylashuvingizni ulang)"
    speech = (f"{len(items)} ta {label.lower()} topdim, ekraningizda ko'rsatdim"
              f"{tail}. Qaysi biri kerak?")
    return {'speech': speech, 'ui': ui.card_list(ss.ref, items)}
