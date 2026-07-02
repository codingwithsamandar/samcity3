"""To'lov shlyuzi uchun umumiy "to'lanadigan obyektlar" registri.

Payme va Click bir xil registrdan foydalanadi. Har bir tur uchun: obyektni
topish, summasini olish, to'langan-yo'qligini bilish, to'langan/bekor deb
belgilash funksiyalari aniqlanadi.

target_type kalitlari Payme account / Click merchant_trans_id da ishlatiladi:
    order   → delivery.Order
    trip    → taxi.Trip
    booking → booking.VenueBooking
    service → payments.ServicePayment
"""
from django.utils import timezone


# ── Har bir tur uchun amallar ────────────────────────────────────────────────

def _order_get(pk):
    from delivery.models import Order
    return Order.objects.filter(pk=pk).first()

def _order_owner(o):
    return o.user_id

def _order_amount(o):
    return int(o.total)

def _order_is_paid(o):
    return o.payment_status == 'paid'

def _order_mark_paid(o):
    o.payment_status = 'paid'
    update_fields = ['payment_status']
    # Pickup (olib ketish) buyurtmasi: to'lov MAJBURIY oldindan. To'langach
    # buyurtma avtomatik 'to'landi' (accepted) holatiga o'tadi va do'kon egasi
    # xabardor qilinadi. Yetkazib berish buyurtmalari bu yerda o'zgarmaydi
    # (ular egasi tomonidan qo'lda qabul qilinadi).
    if o.fulfillment_type == 'pickup' and o.status == 'pending':
        o.status = 'accepted'
        update_fields.append('status')
    o.save(update_fields=update_fields)
    if o.fulfillment_type == 'pickup' and 'status' in update_fields:
        _notify_pickup_paid(o)


def _notify_pickup_paid(order):
    """Pickup buyurtma to'langach do'kon egasiga bildirishnoma (best-effort)."""
    try:
        from notifications.models import notify
        from django.urls import reverse
        store = None
        first = order.items.first()
        if first and first.product and first.product.store:
            store = first.product.store
        if store is None:
            return
        url = reverse('delivery:store_orders')
        notify(store.owner, "Yangi olib ketish buyurtmasi to'landi 🛍️", url, 'order')
    except Exception:
        pass

def _order_mark_unpaid(o):
    o.payment_status = 'unpaid'
    o.save(update_fields=['payment_status'])


def _trip_get(pk):
    from taxi.models import Trip
    return Trip.objects.filter(pk=pk).first()

def _trip_owner(t):
    return t.passenger_id

def _trip_amount(t):
    return int(t.price)

def _trip_is_paid(t):
    return t.payment_status == 'paid'

def _trip_mark_paid(t):
    t.payment_status = 'paid'
    t.save(update_fields=['payment_status'])

def _trip_mark_unpaid(t):
    t.payment_status = 'unpaid'
    t.save(update_fields=['payment_status'])


def _booking_get(pk):
    from booking.models import VenueBooking
    return VenueBooking.objects.filter(pk=pk).first()

def _booking_owner(b):
    return b.user_id

def _booking_amount(b):
    return int(b.total_amount or 0)

def _booking_is_paid(b):
    # Bronda alohida payment_status yo'q — to'langan bron "confirmed" bo'ladi.
    return b.status == 'confirmed'

def _booking_mark_paid(b):
    b.status = 'confirmed'
    b.paid_amount = int(b.total_amount or 0)
    b.save(update_fields=['status', 'paid_amount'])

def _booking_mark_unpaid(b):
    if b.status == 'confirmed':
        b.status = 'pending'
        b.paid_amount = 0
        b.save(update_fields=['status', 'paid_amount'])


def _service_get(pk):
    from payments.models import ServicePayment
    return ServicePayment.objects.filter(pk=pk).first()

def _service_owner(s):
    return s.user_id

def _service_amount(s):
    return int(s.amount)

def _service_is_paid(s):
    return s.status == 'paid'

def _service_mark_paid(s):
    s.status = 'paid'
    s.paid_at = timezone.now()
    s.save(update_fields=['status', 'paid_at'])

def _service_mark_unpaid(s):
    s.status = 'failed'
    s.save(update_fields=['status'])


# ── Registr ──────────────────────────────────────────────────────────────────
PAYABLES = {
    'order': dict(get=_order_get, owner=_order_owner, amount=_order_amount,
                  is_paid=_order_is_paid, mark_paid=_order_mark_paid,
                  mark_unpaid=_order_mark_unpaid),
    'trip': dict(get=_trip_get, owner=_trip_owner, amount=_trip_amount,
                 is_paid=_trip_is_paid, mark_paid=_trip_mark_paid,
                 mark_unpaid=_trip_mark_unpaid),
    'booking': dict(get=_booking_get, owner=_booking_owner, amount=_booking_amount,
                    is_paid=_booking_is_paid, mark_paid=_booking_mark_paid,
                    mark_unpaid=_booking_mark_unpaid),
    'service': dict(get=_service_get, owner=_service_owner, amount=_service_amount,
                    is_paid=_service_is_paid, mark_paid=_service_mark_paid,
                    mark_unpaid=_service_mark_unpaid),
}

# Payme account / boshqa joylarda ishlatiladigan kalit nomlari
ACCOUNT_KEYS = {
    'order_id': 'order',
    'trip_id': 'trip',
    'booking_id': 'booking',
    'service_id': 'service',
}


def resolve_target(target_type, target_id):
    """(obyekt, ops) qaytaradi yoki topilmasa (None, ops/None)."""
    ops = PAYABLES.get(target_type)
    if ops is None:
        return None, None
    return ops['get'](target_id), ops


def target_from_account(account: dict):
    """Payme account dict'idan (target_type, target_id) ajratadi.

    Masalan {"order_id": "..."} → ("order", "...").
    """
    if not isinstance(account, dict):
        return None, None
    for key, ttype in ACCOUNT_KEYS.items():
        if key in account and account[key]:
            return ttype, str(account[key])
    return None, None
