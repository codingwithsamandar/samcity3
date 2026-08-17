"""Yetkazib berish vaqti taxmini — haqiqiy yetkazishlarga tayangan.

Nega kerak: mijoz "qachon keladi?" deb so'raydi, kuryer esa buyurtmani
qabul qilishdan oldin "bu qancha vaqt oladi?" degan savolga javob istaydi.

Ikki bosqichli taxmin:
  1. Masofa — do'kondan mijozgacha (to'g'ri chiziq × yo'l koeffitsienti).
  2. Tezlik — SHU transport turida haqiqatda qanchalik tez borilgan
     (`assigned_at` → `delivered_at`). Yetarli tarix bo'lmasa, standart
     shahar tezligi ishlatiladi.

Mediana ishlatiladi: bitta uzoq kechikkan yetkazish (kuryer telefonini
unutgan) o'rtachani buzadi, medianaga esa deyarli ta'sir qilmaydi.
"""
import math
from statistics import median

# To'g'ri chiziq masofasini haqiqiy yo'lga yaqinlashtirish koeffitsienti.
# Shahar ko'chalari to'g'ri chiziq emas — burilishlar ~30% qo'shadi.
ROAD_FACTOR = 1.3

# Standart shahar tezligi (km/soat) — tarix yetarli bo'lmaganda.
# Svetofor, kutish va manzil izlash hisobga olingan (real tezlik past).
DEFAULT_SPEED = {
    'bike': 11.0,
    'moto': 20.0,
    'car': 18.0,       # shahar ichida mototsikldan sekinroq (parkovka, tirbandlik)
}

# Do'kondan chiqishgacha ketadigan qo'shimcha vaqt (yig'ish, kutish).
PICKUP_OVERHEAD_MIN = 7

MIN_SAMPLES = 5       # shundan kam bo'lsa standart tezlik
SAMPLE_LIMIT = 40     # oxirgi shuncha yetkazish


def haversine_km(lat1, lon1, lat2, lon2):
    """Ikki nuqta orasidagi to'g'ri chiziq masofasi (km)."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def order_distance_km(order):
    """Do'kondan mijozgacha taxminiy yo'l masofasi (km) yoki None.

    Do'kon — buyurtmadagi birinchi mahsulotning do'koni.
    """
    if order.latitude is None or order.longitude is None:
        return None
    item = order.items.select_related('product__store').first()
    store = getattr(getattr(item, 'product', None), 'store', None)
    if not store or store.latitude is None or store.longitude is None:
        return None
    straight = haversine_km(store.latitude, store.longitude,
                            order.latitude, order.longitude)
    return round(straight * ROAD_FACTOR, 2)


def measured_speed(vehicle_type):
    """Shu transport turidagi haqiqiy o'rtacha tezlik (km/soat) yoki None."""
    from .models import Order

    rows = (Order.objects
            .filter(status='delivered',
                    assigned_at__isnull=False, delivered_at__isnull=False,
                    driver__vehicle_type=vehicle_type,
                    latitude__isnull=False, longitude__isnull=False)
            .select_related('driver')
            .order_by('-delivered_at')[:SAMPLE_LIMIT])

    speeds = []
    for o in rows:
        km = order_distance_km(o)
        if not km:
            continue
        minutes = (o.delivered_at - o.assigned_at).total_seconds() / 60
        # Yaroqsiz o'lchovlar: darhol yopilgan yoki kunlab unutilgan buyurtmalar.
        if not (2 <= minutes <= 180):
            continue
        speeds.append(km / (minutes / 60))

    if len(speeds) < MIN_SAMPLES:
        return None
    return median(speeds)


def estimate_delivery_minutes(order, vehicle_type='moto'):
    """Yetkazish taxmini: (daqiqa, masofa_km, manba) yoki (None, None, None).

    manba: 'measured' — haqiqiy tarixdan, 'default' — standart tezlikdan.
    """
    km = order_distance_km(order)
    if km is None:
        return None, None, None

    speed = measured_speed(vehicle_type)
    source = 'measured'
    if speed is None or speed <= 0:
        speed = DEFAULT_SPEED.get(vehicle_type, DEFAULT_SPEED['moto'])
        source = 'default'

    minutes = int(round(km / speed * 60)) + PICKUP_OVERHEAD_MIN
    return max(minutes, 5), km, source


def estimate_label(order, vehicle_type='moto'):
    """Ko'rsatiladigan matn, masalan «~3.2 km · taxminan 18 daqiqa»."""
    minutes, km, source = estimate_delivery_minutes(order, vehicle_type)
    if minutes is None:
        return None
    return f"~{km} km · taxminan {minutes} daqiqa"
