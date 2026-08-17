"""account bo'limi — foydalanuvchining O'ZIGA tegishli narsalari.

Hozirgача agent «buyurtmalarим/bronlarим» so'ralganда «o'zingiz kiring» deб
ko'rsатма berardi. Bu modul ularни TO'G'RIDAN-to'g'ri ko'rsatadi (o'qish) va
past-xavfли profil o'zgаришини (ism) tasdiq bilan bajaradi.

⚠️ Hamma narsа faqat `ctx.user` ning O'ZINIKI — boshqa foydalanuvchи
ma'lumotига yo'l yo'q (queryset har doim user bo'yicha filtrlanади, executor
esа tasdiqlаган `user`ning o'zига yozади).
"""

from django.db import transaction

from ..registry import executor, propose, tool
from .. import ui


def _url(name, *args):
    from django.urls import reverse
    try:
        return reverse(name, args=args)
    except Exception:
        return ''


# ── profile ──────────────────────────────────────────────────────────────────

@tool(
    section='account', action='profile',
    description="O'z profili: ism, telefon, mahalla.",
    params={},
    auth_required=True,
)
def profile(ctx, **_):
    u = ctx.user
    name = (u.name or '').strip() or "(ism kiritilmagan)"
    phone = (u.phone or '').strip()
    phone_disp = f"+998 {phone}" if phone else "(telefon yo'q)"
    nb = getattr(u, 'neighborhood', None)
    lines = [ui.info_line('Ism', name), ui.info_line('Telefon', phone_disp)]
    if nb is not None:
        lines.append(ui.info_line('Mahalla', nb.name))
        district = getattr(nb, 'district', None)
        if district is not None:
            lines.append(ui.info_line('Tuman', district.name))
    return {'speech': f"{name}, profilингiz ekranda.",
            'ui': {'type': 'confirm', 'title': 'Profil', 'lines': lines,
                   'pending_id': None, 'confirm_label': '', 'cancel_label': ''}}


# ── my_orders (delivery buyurtmalari) ────────────────────────────────────────

@tool(
    section='account', action='my_orders',
    description="O'z buyurtmalari (dostavka) va holati.",
    params={},
    auth_required=True,
)
def my_orders(ctx, **_):
    from delivery.models import Order

    orders = list(Order.objects.filter(user=ctx.user).order_by('-created_at')[:5])
    if not orders:
        return {'speech': "Sizда hali buyurtma yo'q."}
    li = []
    for o in orders:
        li.append({'title': f"Buyurtma · {o.total:,} so'm".replace(',', ' '),
                   'subtitle': f"{o.get_status_display()} · {o.created_at:%d-%m %H:%M}",
                   'url': _url('delivery:order_detail', o.pk), 'icon': '🧾'})
    return {'speech': f"Oxirgi {len(orders)} ta buyurtmangiz, ekranда.",
            'ui': ui.link_list(li)}


# ── my_bookings (joy bronlari) ───────────────────────────────────────────────

@tool(
    section='account', action='my_bookings',
    description="O'z joy bronlari.",
    params={},
    auth_required=True,
)
def my_bookings(ctx, **_):
    from booking.models import VenueBooking

    bks = list(VenueBooking.objects.filter(user=ctx.user)
               .select_related('venue', 'service').order_by('-booking_date',
                                                             '-start_time')[:5])
    if not bks:
        return {'speech': "Sizда hali bron yo'q."}
    li = []
    for b in bks:
        svc = b.service.name if b.service_id else ''
        sub = ' · '.join(p for p in (b.get_status_display(),
                                     f"{b.booking_date:%d-%m}",
                                     f"{b.start_time:%H:%M}" if b.start_time else '',
                                     svc) if p)
        li.append({'title': b.venue.name if b.venue_id else 'Bron',
                   'subtitle': sub, 'url': '', 'icon': '📅'})
    return {'speech': f"Oxirgi {len(bks)} ta broningiz, ekranда.",
            'ui': ui.link_list(li)}


# ── my_trips (taksi safarlari) ───────────────────────────────────────────────

@tool(
    section='account', action='my_trips',
    description="O'z taksi safarlari va holati.",
    params={},
    auth_required=True,
)
def my_trips(ctx, **_):
    from django.conf import settings
    # Taksi arxivlangan — safar tarixi ko'rsatilmaydi.
    if not settings.TAXI_ENABLED:
        return {'speech': "Taksi xizmati hozircha o'chirilgan."}
    from taxi.models import Trip

    trips = list(Trip.objects.filter(passenger=ctx.user)
                 .order_by('-created_at')[:5])
    if not trips:
        return {'speech': "Sizда hali taksi safari yo'q."}
    li = []
    for t in trips:
        price = f"{t.price:,} so'm".replace(',', ' ')
        li.append({'title': f"{t.point_a} → {t.point_b}",
                   'subtitle': f"{t.get_status_display()} · {price} · {t.created_at:%d-%m %H:%M}",
                   'url': '', 'icon': '🚕'})
    return {'speech': f"Oxirgi {len(trips)} ta safaringiz, ekranда.",
            'ui': ui.link_list(li)}


# ── my_ads (e'lonlari) ───────────────────────────────────────────────────────

@tool(
    section='account', action='my_ads',
    description="O'z e'lonlari (marketplace).",
    params={},
    auth_required=True,
)
def my_ads(ctx, **_):
    from main.models import Ad

    ads = list(Ad.objects.filter(user=ctx.user).order_by('-created_at')[:8])
    if not ads:
        return {'speech': "Sizда hali e'lon yo'q."}
    li = []
    for a in ads:
        price = f"{a.price:,} so'm".replace(',', ' ') if a.price else ''
        sub = ' · '.join(p for p in (a.get_status_display(), price) if p)
        li.append({'title': a.title, 'subtitle': sub,
                   'url': _url('ad_detail', a.pk), 'icon': '🏷️'})
    return {'speech': f"{len(ads)} ta e'loningiz, ekranда.",
            'ui': ui.link_list(li)}


# ── change_name (mutating — o'z profilи, tasdiq bilan) ───────────────────────

@tool(
    section='account', action='change_name',
    description="Foydalanuvchining O'Z ismini o'zgartiradi.",
    params={'name': ('str', True, "yangi ism")},
    mutating=True,
    auth_required=True,
)
def change_name(ctx, name):
    new = (name or '').strip()[:100]
    if not new:
        return {'ok': False, 'speech': "Yangi ism bo'sh bo'lishi mumkin emas."}
    old = (ctx.user.name or '').strip() or "(yo'q)"
    lines = [ui.info_line('Hozirgi ism', old), ui.info_line('Yangi ism', new)]
    card = ui.confirm(None, "Ismингizni o'zgartiraymi?", lines=lines,
                      confirm_label="Ha, o'zgartir ✅")
    return propose('do_change_name', payload={'name': new}, summary_card=card,
                   amount=0,
                   speech="Ismингizни o'zgartirishга tayyorman. Tasdiqlang.")


@executor('account', 'do_change_name')
def do_change_name(payload, user):
    """Tasdiqdан keyin ismни yozади. Faqat SHU `user`ning o'z profilи."""
    new = (payload or {}).get('name', '').strip()[:100]
    if not new:
        return {'ok': False, 'reply': "Ism bo'sh — o'zgartirilmadi."}
    with transaction.atomic():
        user.name = new
        user.save(update_fields=['name'])
    return {'ok': True, 'reply': f"Tayyor! ✅ Ismингiz endi «{new}»."}
