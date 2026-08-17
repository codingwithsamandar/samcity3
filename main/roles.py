"""Foydalanuvchi "personalari" — saytni rolga moslash uchun yagona manba.

`User.role` maydoni (main/models.py) faqat 4 ta qiymatni ushlaydi va bir odam
bir vaqtda bir nechta rolda bo'lishi mumkin (kuryer + oddiy xaridor). Shu
sababli UI qarorlari `role` ga emas, SHU YERDAGI persona to'plamiga tayanadi.

Hozircha faqat KURYER personasi to'liq ishlatiladi; qolganlari uchun joy
tayyorlab qo'yilgan (`personas()` ni kengaytirish kifoya, shablonlar emas).

Barcha hisob-kitob request'da keshlanadi — har bir shablon bloki uchun bazaga
qayta bormaymiz.
"""

_CACHE_ATTR = '_samcity_personas'


def personas(request):
    """Request uchun persona ma'lumotlari (dict). Har so'rovda bir marta hisoblanadi."""
    cached = getattr(request, _CACHE_ATTR, None)
    if cached is not None:
        return cached

    data = {
        'is_courier': False,
        'courier': None,
        'courier_available': False,
        'courier_blocked': False,
        'courier_new_orders': 0,
        'courier_active_orders': 0,
        'has_business': False,
        'business_alerts': 0,
        'is_venue_staff': False,
        'staff_today': 0,
    }

    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        data.update(_courier_data(user))
        data.update(_business_data(user))
        data.update(_staff_data(user))

    setattr(request, _CACHE_ATTR, data)
    return data


def _courier_data(user):
    """Kuryer holati + panel badge'lari uchun ikkita yengil COUNT."""
    from delivery.models import DeliveryDriver, Order

    driver = DeliveryDriver.objects.filter(user=user).first()
    if not driver:
        return {}

    out = {
        'is_courier': True,
        'courier': driver,
        'courier_available': driver.is_available and driver.is_active,
        'courier_blocked': not driver.is_active,
    }
    # Bloklangan kuryerga "yangi buyurtma" soni ko'rsatilmaydi — u qabul qila
    # olmaydi (delivery.views._driver_queues bilan bir xil shart).
    if driver.is_active:
        out['courier_new_orders'] = Order.objects.filter(
            status='ready', driver__isnull=True, fulfillment_type='delivery',
        ).count()
    out['courier_active_orders'] = Order.objects.filter(
        driver=driver, status__in=['assigned', 'picked_up', 'on_the_way'],
    ).count()
    return out


def is_courier(user):
    """Views uchun qisqa yordamchi (request yo'q joylarda)."""
    if not user or not user.is_authenticated:
        return False
    from delivery.models import DeliveryDriver
    return DeliveryDriver.objects.filter(user=user).exists()


def _business_data(user):
    """Biznes panel havolasi ko'rsatilsinmi va nechta e'tibor talab qiladi.

    Uch manba: do'kon (delivery.Store), bron joyi (booking.Venue), xaritadagi
    joy (places.Place). Har biri EXISTS bilan tekshiriladi — to'liq ro'yxat
    kerak emas, faqat havolani ko'rsatish/yashirish uchun.
    """
    out = {'has_business': False, 'business_alerts': 0}

    try:
        from delivery.models import Store, Order
        has_store = Store.objects.filter(owner=user).exists()
    except Exception:
        has_store = False
    try:
        from booking.models import Venue, VenueBooking
        has_venue = Venue.objects.filter(owner=user).exists()
    except Exception:
        has_venue = False
    try:
        from places.models import Place
        has_place = Place.objects.filter(owner=user).exists()
    except Exception:
        has_place = False

    if not (has_store or has_venue or has_place):
        return out
    out['has_business'] = True

    # Badge — faqat javob kutayotgan ishlar (yangi buyurtma + tasdiqlanmagan bron)
    alerts = 0
    if has_store:
        alerts += Order.objects.filter(
            items__product__store__owner=user, status='pending').distinct().count()
    if has_venue:
        alerts += VenueBooking.objects.filter(
            venue__owner=user, status='pending').count()
    out['business_alerts'] = alerts
    return out


def _staff_data(user):
    """Usta paneli havolasi — foydalanuvchi biror joyda usta sifatida bog'langanmi.

    Bog'lanish `VenueStaff.user` orqali: egasi ustani telefon raqami bilan
    qo'shganda hisob topilsa avtomatik o'rnatiladi.
    """
    out = {'is_venue_staff': False, 'staff_today': 0}
    try:
        from booking.models import VenueStaff, VenueBooking
    except Exception:
        return out

    ids = list(VenueStaff.objects.filter(user=user, is_active=True)
               .values_list('id', flat=True))
    if not ids:
        return out

    from django.utils import timezone
    out['is_venue_staff'] = True
    out['staff_today'] = VenueBooking.objects.filter(
        staff_id__in=ids, booking_date=timezone.localdate(),
        status__in=('pending', 'confirmed')).count()
    return out
