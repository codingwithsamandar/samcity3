import math
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg, Count
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from main.utils import validate_file_type
from .models import (
    TaxiService, ServiceReview, Taxist, Route, TaxistReview,
    Car, Trip, Payment,
)
from .realtime import push_trip_location, push_trip_status


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    try:
        dlat, dlng = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) *
             math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    except (TypeError, ValueError):
        return 1e9


def _fare_rates():
    """Default fare rates from the cheapest active service (or sane defaults)."""
    svc = TaxiService.objects.filter(is_active=True, price_per_km__gt=0).order_by('price_per_km').first()
    if svc:
        return svc.base_price or 5000, svc.price_per_km or 2000
    return 5000, 2000


# ── TAXI MAP: booking + live driver discovery ────────────────────────────────
def taxi_map(request):
    """Ride-hailing style booking map (pickup, destination, nearby drivers, fare)."""
    return render(request, 'taxi/taxi_map.html', {})


def taxi_nearby_drivers(request):
    """Online taxists near a point. GET lat,lng → sorted list with ETA."""
    try:
        lat, lng = float(request.GET.get('lat')), float(request.GET.get('lng'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'bad_coords'}, status=400)
    drivers = []
    qs = (Taxist.objects.filter(is_online=True, is_active=True, latitude__isnull=False)
          .select_related('car'))
    for t in qs:
        d = round(_haversine(lat, lng, t.latitude, t.longitude), 2)
        if d > 15:  # within ~15 km
            continue
        try:
            car_name = t.car.full_name  # reverse OneToOne may not exist
        except Exception:
            car_name = t.car_model or ''
        drivers.append({
            'id': str(t.id), 'name': t.full_name, 'phone': t.phone,
            'car': car_name,
            'lat': t.latitude, 'lng': t.longitude, 'distance_km': d,
            'eta_min': max(1, round(d / 0.5)),  # ~30 km/h → 0.5 km/min
            'rating': t.avg_rating,
        })
    drivers.sort(key=lambda x: x['distance_km'])
    return JsonResponse({'ok': True, 'drivers': drivers[:15]})


def taxi_estimate(request):
    """Fare + distance estimate. GET from=lat,lng to=lat,lng."""
    def _pair(v):
        try:
            a, b = (v or '').split(',')
            return float(a), float(b)
        except (ValueError, AttributeError):
            return None
    src, dst = _pair(request.GET.get('from')), _pair(request.GET.get('to'))
    if not src or not dst:
        return JsonResponse({'ok': False, 'error': 'bad_coords'}, status=400)
    km = round(_haversine(src[0], src[1], dst[0], dst[1]), 2)
    base, per_km = _fare_rates()
    fare = int(base + per_km * km)
    return JsonResponse({
        'ok': True, 'distance_km': km, 'fare': fare,
        'eta_min': max(1, round(km / 0.5)),
        'base': base, 'per_km': per_km,
    })


@login_required
@require_POST
def taxi_update_location(request):
    """Taksist o'z joylashuvini yuboradi (live tracking)."""
    taxist = Taxist.objects.filter(user=request.user).first()
    if not taxist:
        return JsonResponse({'ok': False, 'error': 'not_a_taxist'}, status=403)
    try:
        lat, lng = float(request.POST.get('lat')), float(request.POST.get('lng'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'bad_coords'}, status=400)
    taxist.latitude, taxist.longitude = lat, lng
    taxist.location_updated_at = timezone.now()
    if 'online' in request.POST:
        taxist.is_online = request.POST.get('online') == '1'
    taxist.save(update_fields=['latitude', 'longitude', 'location_updated_at', 'is_online'])
    # Broadcast to active trips of this taxist
    active = Trip.objects.filter(taxist=taxist, status__in=['accepted', 'on_way']).values_list('id', flat=True)
    for tid in active:
        push_trip_location(tid, lat, lng)
    return JsonResponse({'ok': True, 'broadcast_to': len(active)})


@login_required
def taxi_track(request, trip_id):
    """Passenger live tracking screen for a taxi trip."""
    trip = get_object_or_404(Trip.objects.select_related('taxist'), pk=trip_id)
    is_taxist = trip.taxist and trip.taxist.user_id == request.user.id
    if trip.passenger_id != request.user.id and not is_taxist and not request.user.is_staff:
        messages.error(request, "Bu sayohatni kuzatish huquqingiz yo'q.")
        return redirect('taxi:my_trips')
    return render(request, 'taxi/trip_track.html', {'trip': trip})


# ─────────────────────────────────────────────────────────────────────────────
#  Bosh sahifa
# ─────────────────────────────────────────────────────────────────────────────
def taxi_home(request):
    q = request.GET.get('q', '').strip()

    services = (
        TaxiService.objects.filter(is_active=True)
        .annotate(_avg=Avg('reviews__rating'))
        .order_by('-_avg', 'name')
    )
    taxists = (
        Taxist.objects.filter(is_active=True)
        .select_related('car')
        .prefetch_related('routes')
        .order_by('-trips_count', 'full_name')
    )

    if q:
        services = services.filter(
            Q(name__icontains=q) | Q(short_number__icontains=q) | Q(region__icontains=q)
        )
        taxists = taxists.filter(
            Q(full_name__icontains=q) | Q(routes__point_a__icontains=q) |
            Q(routes__point_b__icontains=q) | Q(car_model__icontains=q)
        ).distinct()

    return render(request, 'taxi/taxi_home.html', {
        'services': services,
        'taxists': taxists,
        'q': q,
    })


# ─────────────────────────────────────────────────────────────────────────────
#  Taksi xizmati batafsil
# ─────────────────────────────────────────────────────────────────────────────
def service_detail(request, pk):
    service = get_object_or_404(TaxiService, pk=pk, is_active=True)

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "Baho berish uchun avval tizimga kiring.")
            return redirect('login')
        rating, comment = _parse_review(request)
        if rating is None:
            messages.error(request, "Baho 1 dan 5 gacha bo'lishi kerak.")
        else:
            ServiceReview.objects.update_or_create(
                service=service, user=request.user,
                defaults={'rating': rating, 'comment': comment},
            )
            messages.success(request, "Sharhingiz saqlandi! ✅")
        return redirect('taxi:service_detail', pk=pk)

    reviews = service.reviews.select_related('user')
    user_review = reviews.filter(user=request.user).first() if request.user.is_authenticated else None

    return render(request, 'taxi/service_detail.html', {
        'service': service,
        'reviews': reviews,
        'user_review': user_review,
    })


# ─────────────────────────────────────────────────────────────────────────────
#  Taksist batafsil — mashina, marshrutlar, buyurtma, baho (cheklangan)
# ─────────────────────────────────────────────────────────────────────────────
def taxist_detail(request, pk):
    taxist = get_object_or_404(
        Taxist.objects.select_related('car').prefetch_related('routes'),
        pk=pk, is_active=True,
    )
    can_review = TaxistReview.can_review(request.user, taxist) if request.user.is_authenticated else False

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "Baho berish uchun avval tizimga kiring.")
            return redirect('login')
        if not can_review:
            messages.error(request, "Baho berish uchun avval shu taksist bilan sayohat qiling.")
            return redirect('taxi:taxist_detail', pk=pk)
        rating, comment = _parse_review(request)
        if rating is None:
            messages.error(request, "Baho 1 dan 5 gacha bo'lishi kerak.")
        else:
            TaxistReview.objects.update_or_create(
                taxist=taxist, user=request.user,
                defaults={'rating': rating, 'comment': comment},
            )
            messages.success(request, "Sharhingiz saqlandi! ✅")
        return redirect('taxi:taxist_detail', pk=pk)

    routes = taxist.routes.filter(is_active=True)
    reviews = taxist.reviews.select_related('user')
    user_review = reviews.filter(user=request.user).first() if request.user.is_authenticated else None

    return render(request, 'taxi/taxist_detail.html', {
        'taxist': taxist,
        'car': getattr(taxist, 'car', None),
        'routes': routes,
        'reviews': reviews,
        'user_review': user_review,
        'can_review': can_review,
    })


# ─────────────────────────────────────────────────────────────────────────────
#  Buyurtma berish — sayohat (Trip) yaratish
# ─────────────────────────────────────────────────────────────────────────────
@login_required
def order_create(request, taxist_pk):
    taxist = get_object_or_404(Taxist, pk=taxist_pk, is_active=True)
    if request.method != 'POST':
        return redirect('taxi:taxist_detail', pk=taxist_pk)

    route = get_object_or_404(Route, pk=request.POST.get('route_id'), taxist=taxist)
    is_delivery = request.POST.get('is_delivery') == '1'
    if is_delivery and route.delivery_price:
        price = route.delivery_price
    else:
        is_delivery = False
        price = route.passenger_price

    trip = Trip.objects.create(
        passenger=request.user, taxist=taxist, route=route,
        point_a=route.point_a, point_b=route.point_b,
        is_delivery=is_delivery, price=price,
        status='accepted', payment_method='card', payment_status='unpaid',
    )
    messages.success(request, "Buyurtma qabul qilindi! Endi to'lovni amalga oshiring.")
    return redirect('taxi:trip_payment', trip_id=trip.id)


# ─────────────────────────────────────────────────────────────────────────────
#  To'lov sahifasi — karta orqali (SIMULYATSIYA)
# ─────────────────────────────────────────────────────────────────────────────
@login_required
def trip_payment(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id, passenger=request.user)

    if trip.is_paid:
        messages.info(request, "Bu sayohat allaqachon to'langan.")
        return redirect('taxi:trip_detail', trip_id=trip.id)

    if request.method == 'POST':
        method = request.POST.get('payment_method', 'card')

        if method == 'cash':
            # Naqd to'lov — haydovchiga to'lanadi, sayohat yakunlanadi
            trip.payment_method = 'cash'
            trip.payment_status = 'paid'
            trip.status = 'completed'
            trip.completed_at = timezone.now()
            trip.save()
            push_trip_status(trip)   # jonli yangilash
            taxist = trip.taxist
            taxist.trips_count = (taxist.trips_count or 0) + 1
            taxist.save(update_fields=['trips_count'])
            messages.success(request, "Buyurtma yakunlandi! Naqd to'lov haydovchiga beriladi. ✅")
            return redirect('taxi:trip_detail', trip_id=trip.id)

        # ── Karta to'lovi (simulyatsiya) ─────────────────────────────────────
        card_number = request.POST.get('card_number', '')
        card_holder = request.POST.get('card_holder', '').strip()
        expiry = request.POST.get('expiry', '').strip()
        cvv = request.POST.get('cvv', '').strip()

        digits = ''.join(c for c in card_number if c.isdigit())
        # Oddiy tekshiruv (haqiqiy validatsiya emas — demo)
        if len(digits) < 16 or len(cvv) < 3 or not expiry:
            messages.error(request, "Karta ma'lumotlari to'liq emas. Tekshirib qaytadan kiriting.")
            return render(request, 'taxi/payment.html', {'trip': trip})

        # DIQQAT: to'liq karta raqami va CVV SAQLANMAYDI — faqat oxirgi 4 raqam.
        Payment.objects.update_or_create(
            trip=trip,
            defaults={
                'user': request.user,
                'amount': trip.price,
                'card_holder': card_holder,
                'card_last4': digits[-4:],
                'card_brand': Payment.detect_brand(digits),
                'status': 'paid',
                'paid_at': timezone.now(),
            },
        )
        trip.payment_method = 'card'
        trip.payment_status = 'paid'
        trip.status = 'completed'
        trip.completed_at = timezone.now()
        trip.save()
        push_trip_status(trip)   # jonli yangilash

        taxist = trip.taxist
        taxist.trips_count = (taxist.trips_count or 0) + 1
        taxist.save(update_fields=['trips_count'])

        messages.success(request, "To'lov muvaffaqiyatli amalga oshirildi! ✅")
        return redirect('taxi:trip_detail', trip_id=trip.id)

    return render(request, 'taxi/payment.html', {'trip': trip})


# ─────────────────────────────────────────────────────────────────────────────
#  Sayohat batafsil — holat, to'lov, baho qoldirish (faqat yakunlangan bo'lsa)
# ─────────────────────────────────────────────────────────────────────────────
@login_required
def trip_detail(request, trip_id):
    trip = get_object_or_404(
        Trip.objects.select_related('taxist', 'taxist__car'),
        pk=trip_id, passenger=request.user,
    )

    if request.method == 'POST' and trip.can_be_reviewed:
        rating, comment = _parse_review(request)
        if rating is None:
            messages.error(request, "Baho 1 dan 5 gacha bo'lishi kerak.")
        else:
            TaxistReview.objects.update_or_create(
                taxist=trip.taxist, user=request.user,
                defaults={'rating': rating, 'comment': comment},
            )
            messages.success(request, "Bahoyingiz uchun rahmat! ✅")
        return redirect('taxi:trip_detail', trip_id=trip.id)

    payment = getattr(trip, 'payment', None)
    user_review = TaxistReview.objects.filter(taxist=trip.taxist, user=request.user).first()

    return render(request, 'taxi/trip_detail.html', {
        'trip': trip,
        'payment': payment,
        'user_review': user_review,
    })


# ─────────────────────────────────────────────────────────────────────────────
#  Mening sayohatlarim
# ─────────────────────────────────────────────────────────────────────────────
@login_required
def my_trips(request):
    trips = (
        Trip.objects.filter(passenger=request.user)
        .select_related('taxist')
        .order_by('-created_at')
    )
    return render(request, 'taxi/my_trips.html', {'trips': trips})


# ─────────────────────────────────────────────────────────────────────────────
#  Yordamchi
# ─────────────────────────────────────────────────────────────────────────────
def _parse_review(request):
    """rating (1-5) va comment ni o'qiydi. Noto'g'ri bo'lsa rating=None."""
    try:
        rating = int(request.POST.get('rating'))
    except (TypeError, ValueError):
        return None, ''
    if rating < 1 or rating > 5:
        return None, ''
    return rating, request.POST.get('comment', '').strip()


def _int(v, default=None):
    try:
        return int(str(v).replace(' ', '').replace(',', ''))
    except (TypeError, ValueError):
        return default


# ─────────────────────────────────────────────────────────────────────────────
#  HAYDOVCHI (taksist) o'zini ro'yxatdan o'tkazish / boshqarish
# ─────────────────────────────────────────────────────────────────────────────
def _ensure_taxi_service():
    """Kamida bitta faol TaxiService bo'lishini ta'minlaydi."""
    svc = TaxiService.objects.filter(is_active=True).first()
    if svc:
        return svc
    return TaxiService.objects.create(
        name='SamCity Taksi', short_number='1265', is_active=True,
        working_hours='24/7', base_price=5000, price_per_km=2000,
    )


def _save_taxist_from_post(request, taxist):
    """POST dan taksist profili va mashina ma'lumotini yozadi."""
    taxist.full_name = request.POST.get('full_name', '').strip()
    taxist.phone = request.POST.get('phone', '').strip()
    taxist.car_model = (request.POST.get('brand', '').strip() + ' ' + request.POST.get('model', '').strip()).strip()
    taxist.region = request.POST.get('region', '').strip() or 'Shofirkon'
    svc_id = request.POST.get('service')
    taxist.service = TaxiService.objects.filter(pk=svc_id).first() if svc_id else None
    if not taxist.service:
        taxist.service = _ensure_taxi_service()
    photo = request.FILES.get('photo')
    if photo:
        try:
            validate_file_type(photo)
            taxist.photo = photo
        except Exception as e:
            messages.error(request, f"Foto: {str(e)}")
    taxist.save()

    # Mashina (Car) — bor bo'lsa yangilash, yo'q bo'lsa yaratish
    car = getattr(taxist, 'car', None) or Car(taxist=taxist)
    car.brand = request.POST.get('brand', '').strip()
    car.model = request.POST.get('model', '').strip()
    car.color = request.POST.get('color', '').strip()
    car.plate_number = request.POST.get('plate_number', '').strip()
    car.year = _int(request.POST.get('year'))
    car.seats = _int(request.POST.get('seats'), 4) or 4
    car.car_class = request.POST.get('car_class', 'econom')
    car.has_conditioner = 'has_conditioner' in request.POST
    car.has_baby_seat = 'has_baby_seat' in request.POST
    car.allows_pets = 'allows_pets' in request.POST
    if car.brand or car.model:
        car.save()


@login_required(login_url='/login/')
def taxist_register(request):
    existing = Taxist.objects.filter(user=request.user).first()
    if existing:
        return redirect('taxi:taxist_manage')

    if request.method == 'POST':
        if not request.POST.get('full_name', '').strip() or not request.POST.get('phone', '').strip():
            messages.error(request, "Ism va telefon majburiy.")
        else:
            try:
                taxist = Taxist(user=request.user, is_active=True)
                _save_taxist_from_post(request, taxist)
            except Exception as e:
                messages.error(request, f"Taksist profili yaratishda xatolik: {e}")
            else:
                messages.success(request, "Taksist profili yaratildi! Endi marshrut qo'shing. ✅")
                return redirect('taxi:taxist_manage')

    _ensure_taxi_service()
    return render(request, 'taxi/taxist_form.html', {
        'mode': 'register',
        'services': TaxiService.objects.filter(is_active=True),
        'car_classes': Car.CLASS_CHOICES,
    })


@login_required(login_url='/login/')
def taxist_edit(request):
    taxist = Taxist.objects.filter(user=request.user).first()
    if not taxist:
        return redirect('taxi:taxist_register')

    if request.method == 'POST':
        if not request.POST.get('full_name', '').strip() or not request.POST.get('phone', '').strip():
            messages.error(request, "Ism va telefon majburiy.")
        else:
            _save_taxist_from_post(request, taxist)
            messages.success(request, "Profil yangilandi. ✅")
            return redirect('taxi:taxist_manage')

    return render(request, 'taxi/taxist_form.html', {
        'mode': 'edit', 'taxist': taxist, 'car': getattr(taxist, 'car', None),
        'services': TaxiService.objects.filter(is_active=True),
        'car_classes': Car.CLASS_CHOICES,
    })


@login_required(login_url='/login/')
def taxist_manage(request):
    taxist = Taxist.objects.filter(user=request.user).select_related('car').first()
    if not taxist:
        return redirect('taxi:taxist_register')
    return render(request, 'taxi/taxist_manage.html', {
        'taxist': taxist, 'car': getattr(taxist, 'car', None),
        'routes': taxist.routes.all(),
    })


@login_required(login_url='/login/')
def route_add(request):
    taxist = get_object_or_404(Taxist, user=request.user)
    if request.method == 'POST':
        a = request.POST.get('point_a', '').strip()
        b = request.POST.get('point_b', '').strip()
        price = _int(request.POST.get('passenger_price'))
        if not a or not b or price is None:
            messages.error(request, "A punkt, B punkt va yo'lovchi narxi majburiy.")
        else:
            Route.objects.create(
                taxist=taxist, point_a=a, point_b=b, passenger_price=price,
                delivery_price=_int(request.POST.get('delivery_price')),
                note=request.POST.get('note', '').strip(), is_active=True,
            )
            messages.success(request, "Marshrut qo'shildi. ✅")
    return redirect('taxi:taxist_manage')


@login_required(login_url='/login/')
def route_delete(request, route_id):
    route = get_object_or_404(Route, pk=route_id, taxist__user=request.user)
    if request.method == 'POST':
        route.delete()
        messages.success(request, "Marshrut o'chirildi.")
    return redirect('taxi:taxist_manage')
