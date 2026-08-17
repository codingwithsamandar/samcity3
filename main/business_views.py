"""Biznes paneli — do'kon, bron joyi va xaritadagi joy egalari uchun.

Nega yagona sahifa: bitta odam bir vaqtda do'kon ham, sartaroshxona ham
ochishi mumkin. Ilgari ular tarqoq sahifalarda edi (`/delivery/stores/my/`,
`/booking/manage/`, `/map/<id>/`) va egasi qaysi biri qayerdaligini eslab
qolishi kerak edi. Panel ularni bir joyga yig'adi va faqat egasida bor
bo'lgan bo'limlarni ko'rsatadi.
"""
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

# Bron joyi turi → panel ko'rinishi. Restoran/kafe menyu bilan ishlaydi,
# sartarosh/salon/sport usta va vaqt-slot bilan, to'yxona kunlik bron bilan.
MENU_VENUE_TYPES = ('restaurant', 'cafe')
STAFF_VENUE_TYPES = ('barber', 'beauty', 'gym')

# Menyusi bo'lishi mumkin bo'lgan xarita joylari (places.MENU_CATEGORIES bilan bir xil)
MENU_PLACE_CATEGORIES = ('restaurant', 'wedding', 'hotel')


def _store_cards(user, today):
    """Do'kon egasining har bir do'koni uchun panel kartochkasi."""
    try:
        from delivery.models import Store, Order, Product
    except Exception:
        return []

    stores = list(
        Store.objects.filter(owner=user)
        .select_related('category', 'neighborhood')
        .annotate(product_count=Count('products', distinct=True))
    )
    if not stores:
        return []

    # Buyurtma sanoqlari BIR so'rovda — har do'kon uchun alohida so'rov (N+1) emas.
    # Pickup va yetkazish AJRATILADI: oqimlari boshqacha. Pickup'da kuryer
    # yo'q — do'kon "tayyor" qiladi va mijoz o'zi keladi, ya'ni egasining
    # e'tibori kerak bo'lgan nuqta ham boshqa: "tayyor, mijoz kutilmoqda".
    counts = (
        Order.objects
        .filter(items__product__store__owner=user)
        .values('items__product__store_id')
        .annotate(
            yangi=Count('id', filter=Q(status='pending'), distinct=True),
            faol=Count('id', filter=Q(status__in=(
                'accepted', 'preparing', 'ready', 'assigned',
                'picked_up', 'on_the_way')), distinct=True),
            bugun=Count('id', filter=Q(created_at__date=today), distinct=True),
            # Tayyor qilingan, mijoz kelib olishini kutayotgan buyurtmalar.
            pickup_kutmoqda=Count('id', filter=Q(
                fulfillment_type='pickup', status='ready'), distinct=True),
            pickup_jami=Count('id', filter=Q(
                fulfillment_type='pickup'), distinct=True),
        )
    )
    by_store = {c['items__product__store_id']: c for c in counts}

    cards = []
    for s in stores:
        c = by_store.get(s.pk, {})
        cards.append({
            'obj': s,
            'yangi': c.get('yangi', 0),
            'faol': c.get('faol', 0),
            'bugun': c.get('bugun', 0),
            'mahsulot': s.product_count,
            'pickup_yoqilgan': s.pickup_enabled,
            'pickup_kutmoqda': c.get('pickup_kutmoqda', 0),
            'pickup_jami': c.get('pickup_jami', 0),
        })
    return cards


def _venue_cards(user, today):
    """Bron joylari — sartaroshxona, restoran, to'yxona va h.k."""
    try:
        from booking.models import Venue, VenueBooking
    except Exception:
        return []

    venues = list(
        Venue.objects.filter(owner=user)
        .select_related('place')
        .annotate(
            xizmat_soni=Count('services', filter=Q(services__is_active=True), distinct=True),
            usta_soni=Count('staff', filter=Q(staff__is_active=True), distinct=True),
            ish_soni=Count('works', filter=Q(works__is_active=True), distinct=True),
        )
    )
    if not venues:
        return []

    counts = (
        VenueBooking.objects
        .filter(venue__owner=user)
        .values('venue_id')
        .annotate(
            yangi=Count('id', filter=Q(status='pending')),
            bugun=Count('id', filter=Q(booking_date=today,
                                       status__in=('pending', 'confirmed'))),
            hafta=Count('id', filter=Q(booking_date__gte=today,
                                       booking_date__lt=today + timedelta(days=7),
                                       status__in=('pending', 'confirmed'))),
        )
    )
    by_venue = {c['venue_id']: c for c in counts}

    cards = []
    for v in venues:
        c = by_venue.get(v.pk, {})
        cards.append({
            'obj': v,
            'yangi': c.get('yangi', 0),
            'bugun': c.get('bugun', 0),
            'hafta': c.get('hafta', 0),
            'xizmat': v.xizmat_soni,
            'usta': v.usta_soni,
            'ish': v.ish_soni,
            # Ko'rinishni turga moslash
            'menyuli': v.venue_type in MENU_VENUE_TYPES,
            'ustali': v.venue_type in STAFF_VENUE_TYPES,
        })
    return cards


def _place_cards(user):
    """Xaritadagi joylar — shifoxona, dorixona, restoran va h.k."""
    try:
        from places.models import Place
    except Exception:
        return []

    places = list(
        Place.objects.filter(owner=user)
        .annotate(
            sharh_soni=Count('reviews', distinct=True),
            menyu_soni=Count('menu_items', filter=Q(menu_items__is_active=True),
                             distinct=True),
        )
    )
    return [{
        'obj': p,
        'korish': p.views,
        'sharh': p.sharh_soni,
        'baho': p.avg_rating,
        'menyu': p.menyu_soni,
        'menyuli': p.category in MENU_PLACE_CATEGORIES,
    } for p in places]


@login_required(login_url='/login/')
def business_panel(request):
    """Biznes paneli — egasida bor bo'lgan bo'limlarnigina ko'rsatadi."""
    today = timezone.localdate()
    stores = _store_cards(request.user, today)
    venues = _venue_cards(request.user, today)
    places = _place_cards(request.user)

    return render(request, 'business_panel.html', {
        'stores': stores,
        'venues': venues,
        'places': places,
        'hech_narsa_yoq': not (stores or venues or places),
        # Yig'ma sanoqlar — sahifa tepasidagi qisqa xulosa uchun
        'jami_yangi_buyurtma': sum(c['yangi'] for c in stores),
        'jami_pickup_kutmoqda': sum(c['pickup_kutmoqda'] for c in stores),
        'jami_yangi_bron': sum(c['yangi'] for c in venues),
        'jami_bugun_bron': sum(c['bugun'] for c in venues),
    })
