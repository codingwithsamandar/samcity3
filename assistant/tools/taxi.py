"""taxi bo'limi — taksi chaqirish: taksist/marshrut topish + sayohat buyurtma.

  find_taxists  — faol taksistlar (o'qish, telefon bilan link_list)
  list_routes   — AB marshrutlar (qayerdan→qayerga, narx) — tanlanadi
  propose_trip  — sayohat buyurtmasi (mutating → confirm_payment → Trip)

`taxi.models` (Taxist/Route/Trip) qayta ishlatiladi. Sayohat naqd to'lov bilan
yaratiladi; haydovchi telefon orqali bog'lanadi.
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from .. import engine, selection as sel, ui
from ..registry import executor, propose, tool


def _som(v):
    try:
        return f"{int(v):,}".replace(',', ' ') + " so'm"
    except (TypeError, ValueError):
        return str(v)


# ── find_taxists ─────────────────────────────────────────────────────────────

@tool(
    section='taxi', action='find_taxists',
    description="Faol taksistlarни ko'rsatadi (ism, mashina, telefon). Foydalanuvchi "
                "to'g'ridan-to'g'ri qo'ng'iroq qilib chaqirishi mumkin.",
    params={},
)
def find_taxists(ctx, **_):
    from taxi.models import Taxist

    qs = Taxist.objects.filter(is_active=True).order_by('-is_online', '-trips_count')
    taxists = list(qs[:8])
    if not taxists:
        return {'speech': "Hozircha faol taksist topilmadi."}
    items = []
    for t in taxists:
        sub = t.car_model or 'Taksi'
        if t.trips_count:
            sub += f" · {t.trips_count} sayohat"
        tags = ['🟢 Onlayn'] if t.is_online else []
        items.append({'title': t.full_name, 'subtitle': sub, 'phone': t.phone or '',
                      'tags': tags, 'icon': '🚕'})
    return {'speech': f"{len(items)} ta taksist bor, ekraningizda. Qo'ng'iroq qilish "
                      f"uchun tugmani bosing, yoki marshrut bo'yicha buyurtma bering.",
            'ui': ui.link_list(items)}


# ── list_routes ──────────────────────────────────────────────────────────────

@tool(
    section='taxi', action='list_routes',
    description="AB marshrutlarни (qayerdan qayerga, narxi bilan) ko'rsatadi. "
                "Manzil berilsa (masalan «Buxoro») shu bo'yicha filtrlaydi.",
    params={
        'destination': ('str', False, "qayerga (masalan «Buxoro», «bozor») — ixtiyoriy"),
    },
)
def list_routes(ctx, destination=''):
    from taxi.models import Route

    qs = Route.objects.filter(is_active=True, taxist__is_active=True).select_related('taxist')
    terms = engine._search_terms(destination) if destination else []
    if terms:
        qs = qs.filter(engine._icontains_q(terms, ['point_a', 'point_b', 'note']))
    routes = list(qs[:10])
    if not routes:
        return {'speech': "Bu yo'nalishда marshrut topilmadi. Taksistlarني "
                          "ko'rib, to'g'ridan-to'g'ri qo'ng'iroq qilishни xohlaysizmi?"}
    items = []
    for i, r in enumerate(routes, start=1):
        items.append({
            'id': f'route:{r.pk}', 'index': i,
            'title': f"{r.point_a} → {r.point_b}",
            'subtitle': f"{_som(r.passenger_price)} · {r.taxist.full_name}",
            'aliases': [engine._norm(f"{r.point_a} {r.point_b}")],
            'route_id': str(r.pk), 'price': int(r.passenger_price)})
    ss = sel.create(ctx, 'taxi', items)
    return {'speech': f"{len(items)} ta marshrut topdim, ekraningizda. Qaysi biriga "
                      f"buyurtma beramiz?",
            'ui': ui.card_list(ss.ref, items)}


# ── propose_trip (mutating) ──────────────────────────────────────────────────

@tool(
    section='taxi', action='propose_trip',
    description="Tanlangан marshrut bo'yicha taksi buyurtmasини tasdiqqa tayyorlaydi. "
                "list_routes'даги route ID'sини ber.",
    params={'route_id': ('str', True, "marshrut ID (list_routes natijasidan)")},
    mutating=True,
    auth_required=True,
)
def propose_trip(ctx, route_id):
    from taxi.models import Route

    rid = str(route_id).replace('route:', '').strip()
    try:
        r = Route.objects.filter(pk=rid, is_active=True).select_related('taxist').first()
    except (ValueError, ValidationError):
        r = None
    if r is None:
        return {'ok': False, 'speech': "Bunday marshrut topilmadi. Avval "
                                       "marshrutни (list_routes) tanlang."}
    amount = int(r.passenger_price)
    card = ui.confirm_payment(
        pending_id=None,
        lines=[ui.money_line(f"{r.point_a} → {r.point_b}", amount)],
        total=amount,
        note=f"Haydovchi: {r.taxist.full_name} · {r.taxist.phone} · joyda naqd",
    )
    return propose('create_trip',
                   payload={'route_id': str(r.pk)},
                   summary_card=card, amount=amount,
                   speech=f"{r.point_a} dan {r.point_b} ga — {_som(amount)}, haydovchi "
                          f"{r.taxist.full_name}. Tasdiqlash uchun tugmani bosing.")


@executor('taxi', 'create_trip')
def create_trip(payload, user):
    from taxi.models import Route, Trip

    p = payload or {}
    r = Route.objects.filter(pk=p.get('route_id'), is_active=True).select_related('taxist').first()
    if r is None:
        return {'ok': False, 'reply': "Marshrut topilmadi — buyurtma yaratilmadi."}
    with transaction.atomic():
        trip = Trip.objects.create(
            passenger=user, taxist=r.taxist, route=r,
            point_a=r.point_a, point_b=r.point_b,
            price=int(r.passenger_price), status='accepted',
            payment_method='cash', payment_status='unpaid',
        )
    return {'ok': True,
            'reply': f"Taksi buyurtma qabul qilindi! ✅ {r.point_a} → {r.point_b}, "
                     f"{_som(r.passenger_price)}. Haydovchi {r.taxist.full_name} "
                     f"({r.taxist.phone}) bog'lanadi.",
            'trip_id': str(trip.id), 'total': int(r.passenger_price)}
