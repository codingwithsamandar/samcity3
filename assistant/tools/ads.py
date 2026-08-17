"""ads bo'limi — e'lonlar (oldi-sotdi marketplace): qidirish + joylash.

  search  — e'lon qidirish (o'qish, link_list — havolali kartalar)
  post    — YANGI e'lon joylash (mutating → PendingAction → confirm → Ad)

Mavjud `main.models.Ad` va `engine._search_ads` qayta ishlatiladi. E'lon rasmsiz
(faqat matn) joylanadi — chatga rasm yuklab bo'lmaydi; rasm keyin sayt orqali
qo'shiladi.
"""

from django.db import transaction

from .. import engine, selection as sel, ui
from ..registry import executor, propose, tool

# Ad.CATEGORY_CHOICES kalitlari — sxema enum'i (o'zbekcha so'z emas, kalit).
AD_CATEGORIES = ['uy_joy', 'ish', 'avtomobil', 'qishloq', 'xizmat',
                 'hayvonlar', 'boshqa']
_CAT_LABEL = {'uy_joy': 'Uy-joy', 'ish': 'Ish', 'avtomobil': 'Avtomobil',
              'qishloq': "Qishloq xo'jaligi", 'xizmat': 'Xizmat',
              'hayvonlar': 'Hayvonlar', 'boshqa': 'Boshqa'}


def _som(v):
    try:
        return f"{int(v):,}".replace(',', ' ') + " so'm"
    except (TypeError, ValueError):
        return str(v)


# ── search ───────────────────────────────────────────────────────────────────

@tool(
    section='ads', action='search',
    description="E'lonlar (oldi-sotdi) ichidan qidiradi. Faqat qidirish — sotib "
                "olinmaydi. Kam natija bo'lsa yoki «internetdan qidir» desa "
                "external=true (OLX qo'shiladi).",
    params={
        'query': ('str', True, "nima qidiryapsiz, masalan «velosiped»"),
        'category': ('str', False, "toifa filtri", AD_CATEGORIES),
        'external': ('bool', False, "tashqi saytlardan ham qidirish"),
    },
)
def search(ctx, query, category=None, external=None):
    from django.conf import settings

    ads = engine._search_ads(query, limit=8)
    if category in AD_CATEGORIES:
        ads = [a for a in ads if a.category == category]

    # ── Tashqi qidiruv sharti ────────────────────────────────────────────────
    # Uch holatda tashqi saytlardan ham qidiramiz:
    #   1) foydalanuvchi ataylab so'radi (external=true),
    #   2) saytda umuman topilmadi (0 ta),
    #   3) saytda MIN_LOCAL (default 4) tadan kam natija chiqdi.
    min_local = int(getattr(settings, 'ASSISTANT_EXTERNAL_MIN_LOCAL', 4))
    want_external = bool(external) or (len(ads) < min_local)

    ext_listings = []
    if want_external:
        try:
            from .. import external as ext_mod
            ext_listings = ext_mod.search(query, limit=6, category=category)
        except Exception:  # noqa: BLE001 — tashqi qidiruv chatni buzmasin
            ext_listings = []

    # Tashqi natija yo'q (qidiruv o'chiq yoki hech narsa topilmadi), lekin sayt
    # e'lonlari bor — eski, TANLANADIGAN oqim: foydalanuvchi «batafsil» deya oladi.
    if not ext_listings and ads:
        items = [_ad_pick_item(a, i) for i, a in enumerate(ads, start=1)]
        ss = sel.create(ctx, 'ads', items)
        return {'speech': f"{len(items)} ta e'lon topdim, ekraningizda. Batafsil "
                          f"ma'lumot uchun qaysинини ayting.",
                'ui': ui.card_list(ss.ref, items)}

    # Aks holda: sayt natijalari (bo'lsa) + tashqi manbalar birga (link_list).
    cards = [_ad_link_card(a) for a in ads]
    cards.extend(l.to_card() for l in ext_listings)

    if not cards:
        return {'speech': "Bu bo'yicha e'lon topilmadi — saytda ham, tashqi saytlarda "
                          "ham. Boshqacharoq qidirib ko'ring yoki o'zingiz e'lon "
                          "joylashni xohlaysizmi?"}

    n_local, n_ext = len(ads), len(ext_listings)
    if n_local and n_ext:
        speech = (f"Saytimizda {n_local} ta, internetdan (OLX) yana {n_ext} ta "
                  f"e'lon topdim. Ekraningizda.")
    elif n_ext:
        speech = (f"Saytimizda topilmadi, lekin internetdan (OLX) {n_ext} ta e'lon "
                  f"topdim. Ekraningizda.")
    else:
        speech = f"{n_local} ta e'lon topdim, ekraningizda."
    return {'speech': speech, 'ui': ui.link_list(cards)}


def _ad_price(a):
    if a.price_type == 'free':
        return 'Bepul'
    if a.price:
        return _som(a.price)
    return ''


def _ad_pick_item(a, i):
    """Sayt e'lonini card_list (TANLANADIGAN) elementiga aylantiradi."""
    from django.urls import reverse
    price = _ad_price(a)
    sub = ' · '.join(p for p in (price, a.location or a.get_category_display()) if p)
    try:
        url = reverse('ad_detail', args=[a.pk])
    except Exception:
        url = ''
    # ⚠️ card_list + SelectionSet — «u haqида batafsil», «birinchisi» yechilsin.
    return {'id': f'ad:{a.pk}', 'index': i, 'ad_id': str(a.pk),
            'title': a.title, 'subtitle': sub, 'url': url,
            'aliases': [a.title.lower()],
            'price': (a.price or None),
            'phone': a.contact_phone or '', 'icon': '🏷️'}


def _ad_link_card(a):
    """Sayt e'lonini link_list kartasiga aylantiradi (tashqi bilan aralashganda)."""
    from django.urls import reverse
    price = _ad_price(a)
    sub = ' · '.join(p for p in (price, a.location or a.get_category_display()) if p)
    try:
        url = reverse('ad_detail', args=[a.pk])
    except Exception:
        url = ''
    return {'title': a.title, 'subtitle': sub, 'url': url,
            'phone': a.contact_phone or '', 'tags': ['Bizda'], 'icon': '🏷️'}


# ── details ──────────────────────────────────────────────────────────────────

@tool(
    section='ads', action='details',
    description="Bitta e'lonning to'liq ma'lumoti (tavsif, narx, aloqa).",
    params={'ad_id': ('str', True, "search natijasidagi ID")},
)
def details(ctx, ad_id):
    from django.core.exceptions import ValidationError
    from django.urls import reverse
    from main.models import Ad

    aid = str(ad_id).replace('ad:', '').strip()
    try:
        ad = Ad.objects.filter(pk=aid, status='active').first()
    except (ValueError, ValidationError):
        ad = None
    if ad is None:
        return {'ok': False, 'speech': "Bunday e'lon topilmadi."}

    price = 'Bepul' if ad.price_type == 'free' else (_som(ad.price) if ad.price else '—')
    lines = [ui.info_line('Narx', price),
             ui.info_line('Toifa', ad.get_category_display())]
    if ad.location:
        lines.append(ui.info_line('Manzil', ad.location))
    if ad.contact_phone:
        lines.append(ui.info_line('Telefon', ad.contact_phone))
    try:
        url = reverse('ad_detail', args=[ad.pk])
    except Exception:
        url = ''
    card = {'type': 'confirm', 'title': ad.title, 'lines': lines,
            'pending_id': None, 'confirm_label': '', 'cancel_label': ''}
    if ad.description:
        card['note'] = ad.description[:400]
    if url:
        card['url'] = url
    return {'speech': f"«{ad.title}» — {price}. Batafsili ekranda.", 'ui': card}


# ── post (mutating) ──────────────────────────────────────────────────────────

@tool(
    section='ads', action='post',
    description="YANGI e'lon joylaydi (oldi-sotdi). Ma'lumot to'planganda chaqir.",
    params={
        'title': ('str', True, "sarlavha"),
        'category': ('str', True, "toifa", AD_CATEGORIES),
        'price': ('int', False, "narx (so'm); bepul bo'lsa 0"),
        'description': ('str', False, "batafsil tavsif"),
        'phone': ('str', False, "aloqa telefoni (bo'sh bo'lsa profildan)"),
    },
    mutating=True,
    auth_required=True,
)
def post(ctx, title, category, price=None, description='', phone=''):
    if category not in AD_CATEGORIES:
        category = 'boshqa'
    price = int(price) if price else None
    phone = (phone or getattr(ctx.user, 'phone', '') or '').strip()

    lines = [ui.info_line('Sarlavha', title),
             ui.info_line('Toifa', _CAT_LABEL.get(category, category)),
             ui.info_line('Narx', _som(price) if price else 'Bepul')]
    if phone:
        lines.append(ui.info_line('Telefon', phone))
    card = ui.confirm(None, "E'lonni joylashtirasizmi?", lines=lines,
                      confirm_label="Joylashtirish ✅")
    speech = (f"«{title}» e'lonini joylashtirishга tayyorman. Tasdiqlash uchun "
              f"tugmani bosing.")
    return propose('create_ad',
                   payload={'title': title[:200], 'category': category,
                            'price': price, 'description': description[:2000],
                            'phone': phone[:20]},
                   summary_card=card, amount=0, speech=speech)


# ── list_my (o'z e'lonlari — bekor qilish uchun tanlov) ──────────────────────

@tool(
    section='ads', action='list_my',
    description="Foydalanuvchining O'Z faol e'lonlari.",
    params={},
    auth_required=True,
)
def list_my(ctx, **_):
    from django.urls import reverse
    from main.models import Ad

    ads = list(Ad.objects.filter(user=ctx.user, status='active')
               .order_by('-created_at')[:10])
    if not ads:
        return {'speech': "Sizда faol e'lon yo'q."}
    items = []
    for a in ads:
        try:
            url = reverse('ad_detail', args=[a.pk])
        except Exception:
            url = ''
        items.append({'title': a.title,
                      'subtitle': f"{_som(a.price) if a.price else 'Bepul'} · ID {a.pk}",
                      'url': url, 'icon': '🏷️'})
    return {'speech': f"{len(ads)} ta faol e'loningiz bor. Bekor qilish uchun "
                      f"qaysинини ayting.",
            'ui': ui.link_list(items)}


# ── cancel (mutating — o'z e'lonini olib tashlash) ───────────────────────────

@tool(
    section='ads', action='cancel',
    description="Foydalanuvchining O'Z e'lonini olib tashlaydi.",
    params={'ad_id': ('str', True, "list_my yoki search natijasidagi ID")},
    mutating=True,
    auth_required=True,
    owns={'ad_id': 'main.Ad'},
)
def cancel(ctx, ad_id):
    from main.models import Ad

    from django.core.exceptions import ValidationError
    aid = str(ad_id).replace('ad:', '').strip()
    try:
        ad = Ad.objects.filter(pk=aid, user=ctx.user).first()
    except (ValueError, ValidationError):
        ad = None
    if ad is None:
        return {'ok': False, 'speech': "Bunday e'lon topilmadi yoki sizники emas."}
    if ad.status != 'active':
        return {'ok': False, 'speech': "Bu e'lon allaqачон faol emas."}
    lines = [ui.info_line('E\'lon', ad.title),
             ui.info_line('Narx', _som(ad.price) if ad.price else 'Bepul')]
    card = ui.confirm(None, "E'lonni bekor qilasizmi?", lines=lines,
                      confirm_label="Ha, bekor qil ✅", cancel_label="Yo'q")
    return propose('do_cancel_ad', payload={'ad_id': str(ad.pk)},
                   summary_card=card, amount=0,
                   speech=f"«{ad.title}» e'lonини bekor qilishга tayyorman. Tasdiqlang.")


@executor('ads', 'do_cancel_ad')
def do_cancel_ad(payload, user):
    from main.models import Ad

    aid = (payload or {}).get('ad_id')
    ad = Ad.objects.filter(pk=aid, user=user).first() if aid else None
    if ad is None:
        return {'ok': False, 'reply': "E'lon topilmadi — bekor qilinmadi."}
    with transaction.atomic():
        ad.status = 'deleted'
        ad.save(update_fields=['status'])
    return {'ok': True, 'reply': f"«{ad.title}» e'loni bekor qilindi. ✅"}


@executor('ads', 'create_ad')
def create_ad(payload, user):
    from main.models import Ad

    p = payload or {}
    title = (p.get('title') or '').strip()
    if not title:
        return {'ok': False, 'reply': "Sarlavha bo'sh — e'lon joylanmadi."}
    with transaction.atomic():
        ad = Ad.objects.create(
            user=user, title=title[:200],
            category=(p.get('category') if p.get('category') in AD_CATEGORIES else 'boshqa'),
            description=(p.get('description') or '')[:2000],
            price=(p.get('price') or None),
            price_type=('free' if not p.get('price') else 'fixed'),
            contact_phone=(p.get('phone') or '')[:20],
            status='active',
        )
    from django.urls import reverse
    try:
        url = reverse('ad_detail', args=[ad.pk])
    except Exception:
        url = ''
    return {'ok': True,
            'reply': f"E'lon joylandi! ✅ «{ad.title}» endi marketplace'да ko'rinadi.",
            'ad_id': str(ad.id), 'url': url}
