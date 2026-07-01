import math
import json
import hashlib
import urllib.request
import urllib.parse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.cache import cache
from django.db.models import Q, F, Count
from django.views.decorators.http import require_POST
from django.urls import reverse

from .models import Place, PlaceImage, PlaceReview, PlaceFavorite, CATEGORY_CHOICES
from main.utils import validate_file_type

# Single source of truth for the map center (Shofirkon shahri markazi).
CENTER = (40.1156, 64.5036)

# OSM-compatible external services (overridable via env).
import os as _os
OSRM_BASE = _os.environ.get('OSRM_BASE', 'https://router.project-osrm.org')
NOMINATIM_BASE = _os.environ.get('NOMINATIM_BASE', 'https://nominatim.openstreetmap.org')
_HTTP_TIMEOUT = 6


def _http_get_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'SamCity/1.0 (location-engine)'})
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    try:
        d = (math.radians(lat2 - lat1), math.radians(lon2 - lon1))
        a = (math.sin(d[0] / 2) ** 2 + math.cos(math.radians(lat1)) *
             math.cos(math.radians(lat2)) * math.sin(d[1] / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    except (TypeError, ValueError):
        return 1e9


def _ffloat(v):
    try:
        return float(str(v).replace(',', '.').strip())
    except (TypeError, ValueError):
        return None


# ── Central map ──────────────────────────────────────────────────────────────
def map_view(request):
    return render(request, 'places/map.html', {
        'categories': CATEGORY_CHOICES,
        'center_lat': CENTER[0], 'center_lng': CENTER[1],
        'active_cat': request.GET.get('category', ''),
    })


def neighborhoods_geojson(request):
    """Mahalla chegaralari (poligonlar) — xaritada ko'rsatish uchun.

    Faqat chegarasi bor mahallalar qaytariladi. Har biri chat xonasiga bog'lanadi.
    """
    from main.models import Neighborhood
    items = []
    qs = (Neighborhood.objects
          .exclude(boundary__isnull=True)
          .select_related('chat_room'))
    for n in qs:
        if not n.boundary:
            continue
        room = getattr(n, 'chat_room', None)
        items.append({
            'id': n.pk,
            'name': n.name,
            'color': n.color or '#3551d1',
            'boundary': n.boundary,          # [[lat,lng], ...]
            'center': n.centroid(),
            'description': n.description,
            'room_url': (reverse('neighborhood_chat_room', args=[room.pk]) if room else ''),
        })
    return JsonResponse({'neighborhoods': items})


def places_geojson(request):
    category = request.GET.get('category', '').strip()
    qs = Place.objects.filter(is_active=True)
    if category:
        qs = qs.filter(category=category)
    data = [{
        'id': p.id, 'name': p.name, 'category': p.category,
        'cat': p.get_category_display(), 'icon': p.icon, 'color': p.color,
        'lat': p.latitude, 'lng': p.longitude, 'address': p.address,
        'phone': p.phone, 'hours': p.working_hours,
        'image': (p.image.url if p.image else ''),
        'desc': (p.description[:140] if p.description else ''),
        'url': reverse('places:place_detail', args=[p.id]),
    } for p in qs]

    # ── Super-app qatlamlari: delivery do'konlari + onlayn taksistlar ──
    # Faqat umumiy ko'rinishda (joy toifasi bo'yicha filtr yo'q bo'lsa) qo'shiladi.
    if not category:
        data += _delivery_points()
        data += _taxi_points()
    return JsonResponse({'places': data})


def _delivery_points():
    """Koordinatasi bor delivery do'konlarini xarita nuqtalariga aylantiradi."""
    try:
        from delivery.models import Store
    except Exception:
        return []
    out = []
    stores = (Store.objects.filter(is_active=True,
                                   latitude__isnull=False, longitude__isnull=False)
              .select_related('category'))
    for s in stores:
        out.append({
            'id': f'store-{s.pk}', 'name': s.name, 'category': 'delivery_store',
            'cat': (s.category.name if s.category else 'Do\'kon'),
            'icon': '🛒', 'color': '#059669',
            'lat': s.latitude, 'lng': s.longitude, 'address': s.address,
            'phone': s.phone, 'hours': '',
            'image': (s.logo.url if s.logo else ''),
            'url': reverse('delivery:store_detail', args=[s.pk]),
        })
    return out


def _taxi_points():
    """Onlayn (joylashuvi bor) taksistlarni xarita nuqtalariga aylantiradi."""
    try:
        from taxi.models import Taxist
    except Exception:
        return []
    out = []
    taxists = Taxist.objects.filter(is_active=True, is_online=True,
                                    latitude__isnull=False, longitude__isnull=False)
    for t in taxists:
        out.append({
            'id': f'taxi-{t.pk}', 'name': t.full_name, 'category': 'driver',
            'cat': 'Taksist', 'icon': '🚗', 'color': '#e0a52e',
            'lat': t.latitude, 'lng': t.longitude, 'address': t.region or 'Shofirkon',
            'phone': t.phone, 'hours': '',
            'url': reverse('taxi:taxist_detail', args=[t.pk]),
        })
    return out


# ── Directory ────────────────────────────────────────────────────────────────
def place_list(request, category=None):
    category = category or request.GET.get('category', '')
    q = request.GET.get('q', '').strip()
    qs = Place.objects.filter(is_active=True)
    if category:
        qs = qs.filter(category=category)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(address__icontains=q))

    label = dict(CATEGORY_CHOICES).get(category, '')
    # Mashhur joylar (faqat sayohat bo'limida) — ko'rishlar bo'yicha
    popular = None
    if category == 'tourist':
        popular = Place.objects.filter(is_active=True, category='tourist').order_by('-views')[:6]
    # Trending: eng ko'p sevimliga qo'shilgan / ko'rilgan joylar (faqat filtrsiz ko'rinish)
    trending = None
    if not category and not q:
        trending = (Place.objects.filter(is_active=True)
                    .annotate(fav=Count('favorited_by')).order_by('-fav', '-views')[:6])
    return render(request, 'places/place_list.html', {
        'places': qs, 'categories': CATEGORY_CHOICES,
        'current': category, 'current_label': label, 'q': q,
        'popular': popular, 'trending': trending,
    })


def place_detail(request, pk):
    place = get_object_or_404(Place.objects.prefetch_related('images'), pk=pk, is_active=True)
    # Ko'rishlar hisoblagichi (sessiya bo'yicha bir marta)
    skey = f'viewed_place_{pk}'
    if not request.session.get(skey):
        Place.objects.filter(pk=pk).update(views=F('views') + 1)
        request.session[skey] = True
    others = Place.objects.filter(is_active=True, category=place.category).exclude(pk=pk)
    nearby = sorted(others, key=lambda a: _haversine(place.latitude, place.longitude, a.latitude, a.longitude))[:6]

    reviews = place.reviews.select_related('user')
    my_review = None
    is_favorite = False
    if request.user.is_authenticated:
        my_review = reviews.filter(user=request.user).first()
        is_favorite = PlaceFavorite.objects.filter(place=place, user=request.user).exists()

    return render(request, 'places/place_detail.html', {
        'place': place, 'images': place.images.all(), 'nearby': nearby,
        'reviews': reviews, 'my_review': my_review, 'is_favorite': is_favorite,
        'avg_rating': place.avg_rating, 'review_count': place.review_count,
    })


@login_required(login_url='/login/')
@require_POST
def place_review(request, pk):
    place = get_object_or_404(Place, pk=pk, is_active=True)
    try:
        rating = max(1, min(5, int(request.POST.get('rating', 5))))
    except (TypeError, ValueError):
        rating = 5
    text = request.POST.get('text', '').strip()[:2000]
    PlaceReview.objects.update_or_create(
        place=place, user=request.user, defaults={'rating': rating, 'text': text},
    )
    # Notify the place owner (best-effort)
    if place.owner_id and place.owner_id != request.user.id:
        try:
            from notifications.models import notify
            notify(place.owner, f"Yangi sharh: {place.name} — {rating}★",
                   reverse('places:place_detail', args=[place.pk]), 'system')
        except Exception:
            pass
    messages.success(request, "Sharhingiz saqlandi. Rahmat!")
    return redirect('places:place_detail', pk=pk)


@login_required(login_url='/login/')
@require_POST
def place_favorite_toggle(request, pk):
    place = get_object_or_404(Place, pk=pk, is_active=True)
    fav = PlaceFavorite.objects.filter(place=place, user=request.user).first()
    if fav:
        fav.delete()
        active = False
    else:
        PlaceFavorite.objects.create(place=place, user=request.user)
        active = True
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'favorite': active})
    return redirect('places:place_detail', pk=pk)


# ── ROUTING API (OSRM proxy; reusable by delivery/taxi/places) ───────────────
def route_api(request):
    """Yo'nalish: from/to koordinatalari bo'yicha masofa, ETA va geometriya.

    GET params: from=lat,lng  to=lat,lng  profile=driving|walking
    OSRM ga proksi qiladi; xatolik bo'lsa to'g'ri chiziq + Haversine ga qaytadi.
    Natija 5 daqiqaga keshlanadi.
    """
    def _pair(v):
        try:
            a, b = (v or '').split(',')
            return float(a), float(b)
        except (ValueError, AttributeError):
            return None
    src = _pair(request.GET.get('from'))
    dst = _pair(request.GET.get('to'))
    profile = request.GET.get('profile', 'driving')
    if profile not in ('driving', 'walking'):
        profile = 'driving'
    if not src or not dst:
        return JsonResponse({'ok': False, 'error': 'bad_coords'}, status=400)

    key = 'route:' + hashlib.md5(
        f'{profile}:{src[0]:.4f},{src[1]:.4f}->{dst[0]:.4f},{dst[1]:.4f}'.encode()
    ).hexdigest()
    cached = cache.get(key)
    if cached:
        return JsonResponse(cached)

    straight = round(_haversine(src[0], src[1], dst[0], dst[1]), 2)
    result = {
        'ok': True, 'fallback': True,
        'distance_km': straight,
        'duration_min': max(1, round(straight / (4.5 if profile == 'walking' else 22) * 60)),
        'geometry': [[src[0], src[1]], [dst[0], dst[1]]],
        'steps': [],
    }
    try:
        url = (f'{OSRM_BASE}/route/v1/{profile}/'
               f'{src[1]},{src[0]};{dst[1]},{dst[0]}'
               f'?overview=full&geometries=geojson&steps=true')
        data = _http_get_json(url)
        if data.get('routes'):
            r = data['routes'][0]
            geom = [[c[1], c[0]] for c in r['geometry']['coordinates']]
            steps = []
            for leg in r.get('legs', []):
                for st in leg.get('steps', [])[:60]:
                    m = st.get('maneuver', {})
                    steps.append({
                        'type': m.get('type', ''), 'modifier': m.get('modifier', ''),
                        'name': st.get('name', ''), 'distance': round(st.get('distance', 0)),
                    })
            result = {
                'ok': True, 'fallback': False,
                'distance_km': round(r['distance'] / 1000, 2),
                'duration_min': max(1, round(r['duration'] / 60)),
                'geometry': geom, 'steps': steps,
            }
    except Exception:
        pass  # keep straight-line fallback

    cache.set(key, result, 300)
    return JsonResponse(result)


# ── REVERSE GEOCODING (Nominatim proxy) ──────────────────────────────────────
def reverse_geocode_api(request):
    """lat,lng → manzil (Nominatim). 1 kunga keshlanadi."""
    try:
        lat = float(request.GET.get('lat'))
        lng = float(request.GET.get('lng'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'bad_coords'}, status=400)

    key = f'revgeo:{lat:.4f},{lng:.4f}'
    cached = cache.get(key)
    if cached is not None:
        return JsonResponse({'ok': True, 'address': cached})

    address = ''
    try:
        q = urllib.parse.urlencode({'lat': lat, 'lon': lng, 'format': 'json', 'accept-language': 'uz'})
        data = _http_get_json(f'{NOMINATIM_BASE}/reverse?{q}')
        address = data.get('display_name', '') or ''
    except Exception:
        address = ''
    cache.set(key, address, 60 * 60 * 24)
    return JsonResponse({'ok': True, 'address': address})


@login_required(login_url='/login/')
def my_favorite_places(request):
    favs = (PlaceFavorite.objects.filter(user=request.user)
            .select_related('place').prefetch_related('place__images'))
    return render(request, 'places/favorites.html', {'favorites': favs})


# ── Geolokatsiya — yaqin atrofdagilar (Haversine) ────────────────────────────
def nearby(request):
    lat = _ffloat(request.GET.get('lat'))
    lng = _ffloat(request.GET.get('lng'))
    groups = None
    if lat is not None and lng is not None:
        scored = sorted(
            ((p, round(_haversine(lat, lng, p.latitude, p.longitude), 2))
             for p in Place.objects.filter(is_active=True)),
            key=lambda x: x[1],
        )
        STORE = {'delivery_store', 'furniture', 'electronics'}
        SERVICE = {'pharmacy', 'hospital', 'bank', 'post', 'government', 'organization'}
        groups = {
            'all': scored[:10],
            'stores': [x for x in scored if x[0].category in STORE][:6],
            'tourist': [x for x in scored if x[0].category == 'tourist'][:6],
            'services': [x for x in scored if x[0].category in SERVICE][:6],
        }
    return render(request, 'places/nearby.html', {'groups': groups, 'lat': lat, 'lng': lng})


# ── CRUD ─────────────────────────────────────────────────────────────────────
def _apply(request, place):
    place.name = request.POST.get('name', '').strip() or place.name
    place.category = request.POST.get('category', place.category or 'tourist')
    place.description = request.POST.get('description', '').strip()
    lat = _ffloat(request.POST.get('latitude'))
    lng = _ffloat(request.POST.get('longitude'))
    if lat is not None:
        place.latitude = lat
    if lng is not None:
        place.longitude = lng
    place.address = request.POST.get('address', '').strip()
    place.phone = request.POST.get('phone', '').strip()
    place.working_hours = request.POST.get('working_hours', '').strip()
    place.website = request.POST.get('website', '').strip()
    img = request.FILES.get('image')
    if img:
        try:
            validate_file_type(img)
            place.image = img
        except Exception as e:
            messages.error(request, f"Rasm: {str(e)}")
    place.save()
    for g in request.FILES.getlist('gallery')[:8]:
        try:
            validate_file_type(g)
            PlaceImage.objects.create(place=place, image=g)
        except Exception as e:
            messages.warning(request, f"Galereya rasmi: {str(e)}")


def _form_post(request):
    """Forma qiymatlari: yo'q kalit '' (template crash bo'lmasligi uchun)."""
    from collections import defaultdict
    d = defaultdict(str)
    if request.method == 'POST':
        d.update(request.POST.dict())
    return d


@login_required(login_url='/login/')
def place_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        lat = _ffloat(request.POST.get('latitude'))
        lng = _ffloat(request.POST.get('longitude'))
        if not name or lat is None or lng is None:
            messages.error(request, "Nomi, kenglik (lat) va uzunlik (lng) majburiy.")
            return render(request, 'places/place_form.html', {
                'mode': 'create', 'categories': CATEGORY_CHOICES,
                'post': _form_post(request), 'center_lat': CENTER[0], 'center_lng': CENTER[1],
            })
        place = Place(owner=request.user, latitude=lat, longitude=lng)
        _apply(request, place)
        messages.success(request, "Joy qo'shildi! ✅")
        return redirect('places:place_detail', pk=place.pk)
    return render(request, 'places/place_form.html', {
        'mode': 'create', 'categories': CATEGORY_CHOICES, 'post': _form_post(request),
        'center_lat': CENTER[0], 'center_lng': CENTER[1],
    })


@login_required(login_url='/login/')
def place_edit(request, pk):
    place = get_object_or_404(Place, pk=pk)
    if not (request.user.is_staff or place.owner_id == request.user.id):
        messages.error(request, "Bu joyni tahrirlash huquqingiz yo'q.")
        return redirect('places:place_detail', pk=pk)
    if request.method == 'POST':
        _apply(request, place)
        messages.success(request, "Joy yangilandi. ✅")
        return redirect('places:place_detail', pk=place.pk)
    return render(request, 'places/place_form.html', {
        'mode': 'edit', 'place': place, 'categories': CATEGORY_CHOICES,
        'post': _form_post(request),
        'center_lat': place.latitude, 'center_lng': place.longitude,
    })


@login_required(login_url='/login/')
def place_delete(request, pk):
    place = get_object_or_404(Place, pk=pk)
    if not (request.user.is_staff or place.owner_id == request.user.id):
        messages.error(request, "Ruxsat yo'q.")
        return redirect('places:place_detail', pk=pk)
    if request.method == 'POST':
        place.delete()
        messages.success(request, "Joy o'chirildi.")
        return redirect('places:place_list')
    return render(request, 'places/place_confirm_delete.html', {'place': place})
