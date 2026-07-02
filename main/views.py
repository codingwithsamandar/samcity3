from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta
import random
import string
from django.core.paginator import Paginator
from django.db.models import F, Q
from .models import Ad, AdImage, User, Neighborhood, ChatRoom, ChatMessage, ChatAdmin, ChatMember, Booking, JobAd, ResumeAd, UtilityPayment, BoostPayment, OTPCode
import logging
from .utils import validate_file_type, ratelimit
from sms.backends import send_sms
from telegrambot.delivery import try_send_telegram, telegram_connect_url

logger = logging.getLogger('shofirkon.security')  # audit log (LOGGING root handlerlariga tushadi)
OTP_MAX_ATTEMPTS = 5  # noto'g'ri kod kiritishlar chegarasi (brute-force himoyasi)


def public_profile(request, pk):
    from django.db.models import Sum
    viewed_user = get_object_or_404(User, pk=pk)
    user_ads = viewed_user.ads.filter(status='active').prefetch_related('images')
    ads_count = user_ads.count()
    total_views = viewed_user.ads.aggregate(t=Sum('views'))['t'] or 0
    return render(request, 'public_profile.html', {
        'viewed_user': viewed_user,
        'ads': user_ads,
        'ads_count': ads_count,
        'total_views': total_views,
    })


def home(request):
    # Search & filter
    query = request.GET.get('q', '').strip()
    cat_filter = request.GET.get('cat', '')
    sort = request.GET.get('sort', 'newest')

    ads = Ad.objects.filter(status='active').select_related('user').prefetch_related('images')

    if query:
        from django.db.models import Q
        ads = ads.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(location__icontains=query)
        )

    if cat_filter:
        ads = ads.filter(category=cat_filter)

    if sort == 'price_asc':
        ads = ads.order_by('price')
    elif sort == 'price_desc':
        ads = ads.order_by('-price')
    elif sort == 'popular':
        ads = ads.order_by('-views')
    else:
        ads = ads.order_by('-is_boosted', '-created_at')

    cats = [
        ('uy_joy', 'Uy-joy'),
        ('ish', 'Ish'),
        ('avtomobil', 'Avtomobil'),
        ('xizmat', 'Xizmat'),
        ('qishloq', "Qishloq xo'jaligi"),
        ('hayvonlar', 'Hayvonlar'),
        ('boshqa', 'Boshqa'),
    ]

    # Real stats for hero section
    total_users = User.objects.filter(is_active=True).count()
    active_ads = Ad.objects.filter(status='active').count()

    return render(request, 'home.html', {
        'ads': ads,
        'cats': cats,
        'query': query,
        'cat_filter': cat_filter,
        'sort': sort,
        'total_users': total_users,
        'active_ads': active_ads,
    })


def all_ads(request):
    """Login qilmagan foydalanuvchilar uchun barcha e'lonlar sahifasi."""
    query = request.GET.get('q', '').strip()
    cat_filter = request.GET.get('cat', '')
    sort = request.GET.get('sort', 'newest')
    page = int(request.GET.get('page', 1))

    ads = Ad.objects.filter(status='active').select_related('user').prefetch_related('images')

    if query:
        from django.db.models import Q
        ads = ads.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(location__icontains=query)
        )

    if cat_filter:
        ads = ads.filter(category=cat_filter)

    # ── Advanced filters ──
    location = request.GET.get('location', '').strip()
    if location:
        ads = ads.filter(location__icontains=location)
    price_min = request.GET.get('price_min', '').strip()
    if price_min.isdigit():
        ads = ads.filter(price__gte=int(price_min))
    price_max = request.GET.get('price_max', '').strip()
    if price_max.isdigit():
        ads = ads.filter(price__lte=int(price_max))
    if request.GET.get('has_photo') == '1':
        ads = ads.filter(images__isnull=False).distinct()

    if sort == 'price_asc':
        ads = ads.order_by('price')
    elif sort == 'price_desc':
        ads = ads.order_by('-price')
    elif sort in ('popular', 'views'):
        ads = ads.order_by('-views')
    else:
        ads = ads.order_by('-is_boosted', '-created_at')

    from django.core.paginator import Paginator
    paginator = Paginator(ads, 20)
    page_obj = paginator.get_page(page)

    cats = Ad.CATEGORY_CHOICES
    total_count = ads.count()

    fav_ids = set()
    if request.user.is_authenticated:
        from .models import AdFavorite
        fav_ids = set(AdFavorite.objects.filter(
            user=request.user, ad__in=[a.pk for a in page_obj]
        ).values_list('ad_id', flat=True))

    qs = request.GET.copy()
    qs.pop('page', None)
    query_params = qs.urlencode()

    return render(request, 'all_ads.html', {
        'page_obj': page_obj,
        'ads': page_obj,
        'cats': cats,
        'categories': cats,
        'query': query,
        'cat_filter': cat_filter,
        'sort': sort,
        'total_count': total_count,
        'location': location,
        'price_min': price_min,
        'price_max': price_max,
        'has_photo': request.GET.get('has_photo', ''),
        'fav_ids': fav_ids,
        'query_params': query_params,
        'is_paginated': page_obj.has_other_pages(),
        'paginator': paginator,
    })


@ratelimit('register', limit=5, window=3600, methods=('POST',))
def register(request):
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == "POST":
        phone = request.POST.get('phone') or request.POST.get('username')
        name = request.POST.get('name') or request.POST.get('first_name')
        password = request.POST.get('password')

        if phone:
            phone = '+' + ''.join(filter(str.isdigit, phone)) if phone.startswith('+') else ''.join(filter(str.isdigit, phone))

        _digits = ''.join(filter(str.isdigit, phone or ''))
        if not phone or not password:
            messages.error(request, "Telefon raqami yoki parol xato.")
        elif not (9 <= len(_digits) <= 15):
            # 'abc123', '+998999' (juda qisqa) yoki juda uzun raqamlarni rad etamiz
            messages.error(request, "Telefon raqamini to'g'ri kiriting (masalan: +998901234567).")
        elif User.objects.filter(phone=phone).exists():
            messages.error(request, "Bu raqam band. Iltimos boshqa raqam kiriting.")
        else:
            # Create inactive user
            user = User.objects.create_user(phone=phone, password=password, name=name or "", is_active=False)
            
            # Generate OTP
            code = ''.join(random.choices(string.digits, k=6))
            OTPCode.objects.create(
                phone=phone,
                code=code,
                expires_at=timezone.now() + timedelta(minutes=10)
            )

            # Yuborish: Telegram ulangan bo'lsa Telegram, aks holda SMS
            # (mavjud SMS oqimi o'zgarmaydi).
            if try_send_telegram(phone, code):
                request.session['pending_phone'] = phone
                messages.success(request, "Tasdiqlash kodi Telegram orqali yuborildi. 📨")
                return redirect('verify_otp')
            if not send_sms(phone, f"SamCity tasdiqlash kodi: {code}"):
                logger.warning("OTP SMS yuborilmadi: phone=%s", phone)
            request.session['pending_phone'] = phone
            _url = telegram_connect_url()
            if _url:
                messages.info(
                    request,
                    "Tasdiqlash kodi yuborildi. Telegram orqali tezroq olish uchun "
                    f"botni ulang: {_url}")
            else:
                messages.success(request, "Tasdiqlash kodi yuborildi.")
            return redirect('verify_otp')

    return render(request, 'registration/login.html', {'mode': 'register'})


@ratelimit('otp_verify', limit=10, window=600, methods=('POST',))
def verify_otp(request):
    phone = request.session.get('pending_phone')
    if not phone:
        return redirect('register')

    if request.method == 'POST':
        code = (request.POST.get('code') or '').strip()
        # Eng so'nggi faol (ishlatilmagan, muddati o'tmagan) kodni olamiz
        otp = OTPCode.objects.filter(
            phone=phone, used=False, expires_at__gt=timezone.now()
        ).order_by('-created_at').first()

        if not otp:
            messages.error(request, "Kod muddati o'tgan. Iltimos qaytadan ro'yxatdan o'ting.")
            return redirect('register')

        # Brute-force himoyasi: ko'p noto'g'ri urinishdan keyin kodni bekor qilamiz
        if otp.attempts >= OTP_MAX_ATTEMPTS:
            otp.used = True
            otp.save(update_fields=['used'])
            logger.warning("OTP lockout: phone=%s ip=%s", phone, request.META.get('REMOTE_ADDR'))
            messages.error(request, "Juda ko'p noto'g'ri urinish. Iltimos qaytadan ro'yxatdan o'ting.")
            return redirect('register')

        if otp.code == code:
            otp.used = True
            otp.save(update_fields=['used'])
            user = User.objects.filter(phone=phone).first()
            if not user:
                messages.error(request, "Foydalanuvchi topilmadi.")
                return redirect('register')
            user.is_active = True
            user.save(update_fields=['is_active'])
            login(request, user)
            request.session.pop('pending_phone', None)
            messages.success(request, "Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!")
            return redirect('profile')
        else:
            otp.attempts += 1
            otp.save(update_fields=['attempts'])
            remaining = max(0, OTP_MAX_ATTEMPTS - otp.attempts)
            messages.error(request, f"Tasdiqlash kodi xato. Qolgan urinishlar: {remaining}.")

    return render(request, 'registration/verify_otp.html', {'phone': phone})


@ratelimit('login', limit=10, window=300, methods=('POST',))
def user_login(request):
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        phone = request.POST.get('phone') or request.POST.get('username')
        password = request.POST.get('password')

        if phone:
            phone = '+' + ''.join(filter(str.isdigit, phone)) if phone.startswith('+') else ''.join(filter(str.isdigit, phone))

        user = authenticate(request, username=phone, password=password)
        if not user:
            user = authenticate(request, phone=phone, password=password)

        if user is not None:
            login(request, user)
            return redirect('profile')
        else:
            logger.warning("Failed login: phone=%s ip=%s", phone, request.META.get('REMOTE_ADDR'))
            messages.error(request, "Telefon raqami yoki parol xato.")

    return render(request, 'registration/login.html', {'mode': 'login'})


@login_required
def profile(request):
    from django.db.models import Sum
    user_ads = request.user.ads.all().prefetch_related('images')
    pending_bookings_count = Booking.objects.filter(
        owner=request.user, status='pending'
    ).count()
    # Profile statistika - template da ishlatiladigan
    ads_count = user_ads.exclude(status='deleted').count()
    bookings_count = Booking.objects.filter(buyer=request.user).count()
    total_views = user_ads.aggregate(t=Sum('views'))['t'] or 0
    return render(request, 'profile.html', {
        'ads': user_ads,
        'pending_bookings_count': pending_bookings_count,
        'ads_count': ads_count,
        'bookings_count': bookings_count,
        'total_views': total_views,
    })


@login_required
def profile_edit(request):
    user = request.user

    if request.method == "POST":
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        avatar = request.FILES.get('avatar')

        if phone:
            phone = '+' + ''.join(filter(str.isdigit, phone)) if phone.startswith('+') else ''.join(filter(str.isdigit, phone))

            if user.phone != phone and User.objects.filter(phone=phone).exists():
                messages.error(request, "Bu raqam band. Boshqa raqam kiriting.")
                return redirect('profile_edit')
            user.phone = phone

        if name is not None:
            user.name = name

        # Username (ko'rsatiladigan, noyob). Bo'sh bo'lsa — None.
        username = request.POST.get('username', '').strip()
        if username:
            if user.username != username and User.objects.filter(username=username).exists():
                messages.error(request, "Bu foydalanuvchi nomi band. Boshqasini tanlang.")
                return redirect('profile_edit')
            user.username = username
        elif 'username' in request.POST:
            user.username = None

        email = request.POST.get('email', '').strip()
        if email:
            if user.email != email and User.objects.filter(email=email).exists():
                messages.error(request, "Bu email band. Boshqa email kiriting.")
                return redirect('profile_edit')
            user.email = email
        elif email == '':
            user.email = None

        bio = request.POST.get('bio', '')
        user.bio = bio

        if password:
            user.set_password(password)

        if avatar:
            try:
                validate_file_type(avatar)
                user.avatar = avatar
                user.avatar_url = ''
            except Exception as e:
                messages.error(request, f"Rasm yuklashda xatolik: {str(e)}")
                return redirect('profile_edit')

        user.save()
        messages.success(request, "Profil ma'lumotlari muvaffaqiyatli saqlandi!")
        if password:
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)
        return redirect('profile')

    return render(request, 'profile_edit.html')


def ad_detail(request, pk):
    ad = get_object_or_404(Ad, pk=pk)
    # Bot/takroriy ko'rishni oldini olish — sessiya orqali
    session_key = f'viewed_ad_{pk}'
    if not request.session.get(session_key):
        ad.views += 1
        ad.save(update_fields=['views'])
        request.session[session_key] = True

    user_booking = None
    if request.user.is_authenticated and request.user != ad.user:
        user_booking = Booking.objects.filter(
            ad=ad, buyer=request.user
        ).exclude(status='cancelled').first()

    needs_dates = ad.category in ('uy_joy', 'avtomobil')

    from .models import AdFavorite, AdReport, AdInquiry
    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = AdFavorite.objects.filter(ad=ad, user=request.user).exists()
    inquiries = None
    if request.user.is_authenticated and request.user.id == ad.user_id:
        inquiries = ad.inquiries.select_related('sender')

    return render(request, 'ad_detail.html', {
        'ad': ad,
        'user_booking': user_booking,
        'needs_dates': needs_dates,
        'is_favorite': is_favorite,
        'report_reasons': AdReport.REASON_CHOICES,
        'inquiries': inquiries,
    })


def _form_post(request):
    """Forma qiymatlarini xavfsiz qaytaradi: yo'q kalit '' bo'ladi.

    Shablonlarда `{{ post.title|default:'' }}` kabi ishlatilganda, bo'sh
    QueryDict'da yo'q kalit VariableDoesNotExist (crash) berardi. defaultdict
    yo'q kalitга '' qaytaradi — crash bo'lmaydi (GET'da ham, POST'da ham).
    """
    from collections import defaultdict
    d = defaultdict(str)
    if request.method == 'POST':
        d.update(request.POST.dict())
    return d


# ───────── E'LON YARATISH ─────────
@login_required
def ad_create(request):
    if request.method == 'POST':
        title       = request.POST.get('title', '').strip()
        category    = request.POST.get('category', '')
        description = request.POST.get('description', '').strip()
        price_type  = request.POST.get('price_type', 'fixed')
        price       = request.POST.get('price', None)
        location    = request.POST.get('location', '').strip()
        latitude    = request.POST.get('latitude', None)
        longitude   = request.POST.get('longitude', None)
        images      = request.FILES.getlist('images')

        # Contact info
        contact_phone     = request.POST.get('contact_phone', '').strip()
        contact_telegram  = request.POST.get('contact_telegram', '').strip()
        contact_instagram = request.POST.get('contact_instagram', '').strip()
        contact_facebook  = request.POST.get('contact_facebook', '').strip()

        if not title or not category:
            messages.error(request, "Sarlavha va kategoriya majburiy.")
            return render(request, 'ad_form.html', {'mode': 'create', 'post': _form_post(request),
                          'categories': Ad.CATEGORY_CHOICES, 'price_types': Ad.PRICE_TYPE_CHOICES})

        if price_type not in ('fixed', 'free'):
            price_type = 'fixed'

        if price_type == 'fixed':
            if not price or not str(price).strip():
                messages.error(request, "Belgilangan narx turi uchun narx kiritish majburiy.")
                return render(request, 'ad_form.html', {'mode': 'create', 'post': _form_post(request),
                              'categories': Ad.CATEGORY_CHOICES, 'price_types': Ad.PRICE_TYPE_CHOICES})
            try:
                price_str = str(price).replace(' ', '').replace(',', '').replace('.', '')
                price = int(price_str)
                if price < 0:
                    raise ValueError
            except ValueError:
                messages.error(request, "Narx noto'g'ri kiritildi.")
                return render(request, 'ad_form.html', {'mode': 'create', 'post': _form_post(request),
                              'categories': Ad.CATEGORY_CHOICES, 'price_types': Ad.PRICE_TYPE_CHOICES})
        else:
            price = None

        lat = None
        lng = None
        if latitude:
            try:
                v = float(latitude)
                if -90 <= v <= 90:
                    lat = v
                else:
                    messages.warning(request, "Kenglik -90..90 oralig'ida bo'lishi kerak — joylashuv saqlanmadi.")
            except (TypeError, ValueError):
                messages.warning(request, "Kenglik noto'g'ri kiritildi — joylashuv saqlanmadi.")
        if longitude:
            try:
                v = float(longitude)
                if -180 <= v <= 180:
                    lng = v
                else:
                    messages.warning(request, "Uzunlik -180..180 oralig'ida bo'lishi kerak — joylashuv saqlanmadi.")
            except (TypeError, ValueError):
                messages.warning(request, "Uzunlik noto'g'ri kiritildi — joylashuv saqlanmadi.")

        ad = Ad.objects.create(
            user=request.user,
            title=title,
            category=category,
            description=description,
            price=price,
            price_type=price_type,
            location=location,
            latitude=lat,
            longitude=lng,
            contact_phone=contact_phone,
            contact_telegram=contact_telegram,
            contact_instagram=contact_instagram,
            contact_facebook=contact_facebook,
        )

        for i, img in enumerate(images[:10]):
            try:
                validate_file_type(img)
                AdImage.objects.create(ad=ad, image=img, order=i)
            except Exception as e:
                messages.warning(request, f"Rasm yuklashda xatolik: {str(e)}")

        messages.success(request, "E'lon muvaffaqiyatli joylandi!")
        return redirect('ad_detail', pk=ad.pk)

    return render(request, 'ad_form.html', {
        'mode': 'create',
        'post': _form_post(request),
        'categories': Ad.CATEGORY_CHOICES,
        'price_types': Ad.PRICE_TYPE_CHOICES,
    })


# ───────── E'LON TAHRIRLASH ─────────
@login_required
def ad_edit(request, pk):
    ad = get_object_or_404(Ad, pk=pk)

    if ad.user != request.user:
        messages.error(request, "Bu e'lonni tahrirlash huquqingiz yo'q.")
        return redirect('profile')

    if request.method == 'POST':
        ad.title       = request.POST.get('title', '').strip()
        ad.category    = request.POST.get('category', ad.category)
        ad.description = request.POST.get('description', '').strip()
        ad.price_type  = request.POST.get('price_type', ad.price_type)
        ad.location    = request.POST.get('location', '').strip()
        ad.status      = request.POST.get('status', ad.status)

        lat = request.POST.get('latitude', '')
        lng = request.POST.get('longitude', '')
        if lat:
            try:
                v = float(lat)
                if -90 <= v <= 90:
                    ad.latitude = v
                else:
                    messages.warning(request, "Kenglik -90..90 oralig'ida bo'lishi kerak — joylashuv yangilanmadi.")
            except (TypeError, ValueError):
                messages.warning(request, "Kenglik noto'g'ri kiritildi — joylashuv yangilanmadi.")
        if lng:
            try:
                v = float(lng)
                if -180 <= v <= 180:
                    ad.longitude = v
                else:
                    messages.warning(request, "Uzunlik -180..180 oralig'ida bo'lishi kerak — joylashuv yangilanmadi.")
            except (TypeError, ValueError):
                messages.warning(request, "Uzunlik noto'g'ri kiritildi — joylashuv yangilanmadi.")

        ad.contact_phone     = request.POST.get('contact_phone', '').strip()
        ad.contact_telegram  = request.POST.get('contact_telegram', '').strip()
        ad.contact_instagram = request.POST.get('contact_instagram', '').strip()
        ad.contact_facebook  = request.POST.get('contact_facebook', '').strip()

        price = request.POST.get('price', None)
        if ad.price_type not in ('fixed', 'free'):
            ad.price_type = 'fixed'
        if ad.price_type == 'fixed':
            if not price or not str(price).strip():
                messages.error(request, "Belgilangan narx turi uchun narx kiritish majburiy.")
                return render(request, 'ad_form.html', {
                    'mode': 'edit', 'ad': ad,
                    'categories': Ad.CATEGORY_CHOICES,
                    'price_types': Ad.PRICE_TYPE_CHOICES,
                    'statuses': Ad.STATUS_CHOICES,
                })
            try:
                price_str = str(price).replace(' ', '').replace(',', '').replace('.', '')
                ad.price = int(price_str)
            except ValueError:
                messages.error(request, "Narx noto'g'ri kiritildi.")
                return render(request, 'ad_form.html', {
                    'mode': 'edit', 'ad': ad,
                    'categories': Ad.CATEGORY_CHOICES,
                    'price_types': Ad.PRICE_TYPE_CHOICES,
                    'statuses': Ad.STATUS_CHOICES,
                })
        else:
            ad.price = None

        if not ad.title or not ad.category:
            messages.error(request, "Sarlavha va kategoriya majburiy.")
            return render(request, 'ad_form.html', {
                'mode': 'edit', 'ad': ad,
                'categories': Ad.CATEGORY_CHOICES,
                'price_types': Ad.PRICE_TYPE_CHOICES,
                'statuses': Ad.STATUS_CHOICES,
            })

        # Handle sold status timestamp
        if ad.status == 'sold' and not ad.sold_at:
            ad.sold_at = timezone.now()
        elif ad.status != 'sold':
            ad.sold_at = None

        ad.save()

        delete_imgs = request.POST.getlist('delete_images')
        if delete_imgs:
            AdImage.objects.filter(id__in=delete_imgs, ad=ad).delete()

        new_images = request.FILES.getlist('images')
        existing_count = ad.images.count()
        for i, img in enumerate(new_images[:max(0, 10 - existing_count)]):
            try:
                validate_file_type(img)
                AdImage.objects.create(ad=ad, image=img, order=existing_count + i)
            except Exception as e:
                messages.warning(request, f"Rasm yuklashda xatolik: {str(e)}")

        messages.success(request, "E'lon muvaffaqiyatli yangilandi!")
        return redirect('ad_detail', pk=ad.pk)

    return render(request, 'ad_form.html', {
        'mode': 'edit',
        'ad': ad,
        'post': _form_post(request),
        'categories': Ad.CATEGORY_CHOICES,
        'price_types': Ad.PRICE_TYPE_CHOICES,
        'statuses': Ad.STATUS_CHOICES,
    })


# ───────── E'LON O'CHIRISH ─────────
@login_required
def ad_delete(request, pk):
    ad = get_object_or_404(Ad, pk=pk)

    if ad.user != request.user:
        messages.error(request, "Bu e'lonni o'chirish huquqingiz yo'q.")
        return redirect('profile')

    if request.method == 'POST':
        ad.status = 'deleted'
        ad.save(update_fields=['status'])
        messages.success(request, "E'lon o'chirildi.")
        return redirect('profile')

    return render(request, 'ad_confirm_delete.html', {'ad': ad})


# ───────── E'LON SOTILDI/SOTILMADI TOGGLE ─────────
@login_required
def ad_toggle_sold(request, pk):
    ad = get_object_or_404(Ad, pk=pk)

    if ad.user != request.user:
        messages.error(request, "Ruxsat yo'q.")
        return redirect('ad_detail', pk=pk)

    if request.method == 'POST':
        if ad.status == 'sold':
            ad.status = 'active'
            ad.sold_at = None
            messages.success(request, "E'lon yana faol holatga qaytarildi.")
        else:
            ad.status = 'sold'
            ad.sold_at = timezone.now()
            messages.success(request, "E'lon sotilgan deb belgilandi. Barcha foydalanuvchilar buni ko'radi.")
        ad.save(update_fields=['status', 'sold_at'])

    return redirect('ad_detail', pk=pk)


# ───────── E'LONLARIM (alohida sahifa) ─────────
@login_required
def my_ads(request):
    status_filter = request.GET.get('status', 'all')
    ads = request.user.ads.prefetch_related('images')
    if status_filter != 'all':
        ads = ads.filter(status=status_filter)
    ads = ads.exclude(status='deleted')
    return render(request, 'my_ads.html', {
        'ads': ads,
        'status_filter': status_filter,
        'statuses': Ad.STATUS_CHOICES,
    })


# ───────── MAHALLA CHAT ─────────
def neighborhood_chat(request):
    """Mahalla chatlari ro'yxati — hamma ko'ra oladi."""
    if not Neighborhood.objects.exists():
        default_neighborhoods = [
            ("Umumiy chat", "Barcha foydalanuvchilar uchun umumiy muhokama xonasi"),
            ("E'lonlar", "Mahalliy e'lonlar va xabarlar uchun xona"),
        ]
        for name, desc in default_neighborhoods:
            n, _ = Neighborhood.objects.get_or_create(name=name, defaults={'description': desc})
            ChatRoom.objects.get_or_create(neighborhood=n)

    for neighborhood in Neighborhood.objects.all():
        ChatRoom.objects.get_or_create(neighborhood=neighborhood)

    neighborhoods = list(Neighborhood.objects.select_related('chat_room').prefetch_related(
        'chat_room__messages', 'admins'
    ))

    # Foydalanuvchi tanlagan "o'z mahallasi" — ro'yxat tepasiga pin qilinadi.
    my_neighborhood = None
    if request.user.is_authenticated and request.user.neighborhood_id:
        my_neighborhood = next(
            (n for n in neighborhoods if n.pk == request.user.neighborhood_id), None)
        if my_neighborhood:
            neighborhoods = [my_neighborhood] + [n for n in neighborhoods if n.pk != my_neighborhood.pk]

    return render(request, 'neighborhood_chat.html', {
        'neighborhoods': neighborhoods,
        'my_neighborhood': my_neighborhood,
    })


@login_required
@require_POST
def set_neighborhood(request):
    """Foydalanuvchi o'z mahallasini tanlaydi (yoki bekor qiladi).

    Mahalla tanlanganda foydalanuvchi o'sha mahalla chat guruhiga avtomatik
    (tasdiqlangan a'zo sifatida) qo'shiladi. Mahalla o'zgartirilsa — avvalgi
    guruhdan chiqariladi va yangisiga qo'shiladi.
    """
    old = request.user.neighborhood
    nbhd_id = request.POST.get('neighborhood_id') or ''

    # Eski mahalla guruhidan chiqarish (mahalla o'zgargan yoki bekor qilingan bo'lsa).
    if old and (not nbhd_id or str(old.pk) != str(nbhd_id)):
        old_room = ChatRoom.objects.filter(neighborhood=old).first()
        if old_room:
            ChatMember.objects.filter(room=old_room, user=request.user).delete()

    if nbhd_id:
        nbhd = get_object_or_404(Neighborhood, pk=nbhd_id)
        request.user.neighborhood = nbhd
        request.user.save(update_fields=['neighborhood'])
        # Yangi mahalla guruhiga avtomatik qo'shish (tasdiqlangan a'zo).
        room, _ = ChatRoom.objects.get_or_create(neighborhood=nbhd)
        ChatMember.objects.update_or_create(
            room=room, user=request.user,
            defaults={'is_approved': True, 'is_banned': False, 'approved_at': timezone.now()},
        )
        messages.success(
            request, f"Mahallangiz «{nbhd.name}» deb belgilandi — guruhga qo'shildingiz.")
    else:
        request.user.neighborhood = None
        request.user.save(update_fields=['neighborhood'])
        messages.info(request, "Mahalla belgisi olib tashlandi.")

    # AJAX (popup) so'rovi bo'lsa JSON qaytaramiz.
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True})
    return redirect('neighborhood_chat')


def _enrich_chat_message(msg, request_user):
    """Bitta xabarni shablon uchun tayyorlash (admin anonim ko'rinadi)."""
    if msg.is_admin_message:
        name, initials, is_admin = '🛡️ Admin', 'AD', True
    else:
        name = msg.user.name or msg.user.phone
        parts = name.split()
        initials = (parts[0][0] + parts[1][0]).upper() if len(parts) >= 2 else name[:2].upper()
        is_admin = False

    kind = 'text'
    if msg.image:
        kind = 'image'
    elif msg.audio:
        kind = 'audio'
    elif msg.file:
        kind = 'file'

    reply = None
    if msg.reply_to_id and msg.reply_to and not msg.reply_to.is_deleted:
        r = msg.reply_to
        rtext = r.text or ('📷 Rasm' if r.image else ('🎤 Ovozli xabar' if r.audio else ('📎 Fayl' if r.file else '')))
        reply = {'id': str(r.pk), 'text': rtext[:120],
                 'author': '🛡️ Admin' if r.is_admin_message else (r.user.name or r.user.phone)}

    reactions = {}
    my = set()
    for rx in msg.reactions.all():
        reactions[rx.emoji] = reactions.get(rx.emoji, 0) + 1
        if request_user.is_authenticated and rx.user_id == request_user.id:
            my.add(rx.emoji)

    return {
        'id': str(msg.pk),
        'kind': kind,
        'text': msg.text or '',
        'image_url': msg.image.url if msg.image else None,
        'file_url': msg.file.url if msg.file else None,
        'file_name': (msg.file.name.split('/')[-1] if msg.file else None),
        'audio_url': msg.audio.url if msg.audio else None,
        'time': timezone.localtime(msg.created_at).strftime('%H:%M'),
        'reply': reply,
        'edited': bool(msg.edited_at),
        'forwarded': bool(msg.forwarded_from_id),
        'reactions': reactions,
        'my_reactions': list(my),
        'display_name': name,
        'display_initials': initials,
        'is_admin_msg': is_admin,
        'real_user_id': str(msg.user_id),
        'is_own': request_user.is_authenticated and msg.user_id == request_user.id,
    }


def neighborhood_chat_room(request, room_id):
    """Chat xonasi — hamma o'qiy oladi, faqat ruxsatlilargina yoza oladi."""
    room = get_object_or_404(ChatRoom.objects.select_related('neighborhood'), pk=room_id)
    # Optimallashtirilgan: oxirgi 60 ta xabar, reply va reaksiyalar bilan.
    recent = list(
        room.messages.filter(is_deleted=False)
        .select_related('user', 'reply_to__user')
        .prefetch_related('reactions')
        .order_by('-created_at')[:60]
    )
    recent.reverse()

    is_chat_admin = is_approved = is_banned = False
    pending_count = 0

    if request.user.is_authenticated:
        is_chat_admin = ChatAdmin.objects.filter(neighborhood=room.neighborhood, user=request.user).exists()
        member, _ = ChatMember.objects.get_or_create(
            room=room, user=request.user, defaults={'is_approved': False, 'is_banned': False})
        is_approved = member.is_approved
        is_banned = member.is_banned and not is_chat_admin
        member.last_read_at = timezone.now()
        member.save(update_fields=['last_read_at'])
        if is_chat_admin:
            pending_count = ChatMember.objects.filter(
                room=room, is_approved=False, is_banned=False).exclude(user=request.user).count()

    enriched_messages = [_enrich_chat_message(m, request.user) for m in recent]
    oldest_id = recent[0].pk if recent else ''

    return render(request, 'neighborhood_chat_room.html', {
        'room': room,
        'chat_messages': enriched_messages,
        'oldest_id': oldest_id,
        'is_chat_admin': is_chat_admin,
        'is_approved': is_approved,
        'is_banned': is_banned,
        'pending_count': pending_count,
    })


@login_required
def chat_history(request, room_id):
    """Eski xabarlarni JSON ko'rinishida qaytaradi (infinite scroll)."""
    room = get_object_or_404(ChatRoom, pk=room_id)
    qs = room.messages.filter(is_deleted=False).select_related('user', 'reply_to__user').prefetch_related('reactions')
    before = request.GET.get('before')
    if before:
        try:
            pivot = ChatMessage.objects.get(pk=before)
            qs = qs.filter(created_at__lt=pivot.created_at)
        except (ChatMessage.DoesNotExist, ValueError, TypeError):
            pass
    batch = list(qs.order_by('-created_at')[:40])
    batch.reverse()
    data = [_enrich_chat_message(m, request.user) for m in batch]
    return JsonResponse({'messages': data, 'oldest_id': (batch[0].pk if batch else None)})


# ───────── CHAT ADMIN API ─────────

@login_required
def chat_pending_members(request, room_id):
    """Kutayotgan a'zolar ro'yxati (faqat admin)"""
    room = get_object_or_404(ChatRoom, pk=room_id)
    if not ChatAdmin.objects.filter(neighborhood=room.neighborhood, user=request.user).exists():
        return JsonResponse({'error': 'Ruxsat yo\'q'}, status=403)

    pending = ChatMember.objects.filter(
        room=room, is_approved=False, is_banned=False
    ).select_related('user')

    data = [{
        'user_id': str(m.user.id),
        'name': m.user.name or m.user.phone,
        'phone': m.user.phone,
        'joined_at': timezone.localtime(m.joined_at).strftime('%d.%m.%Y %H:%M'),
    } for m in pending]
    return JsonResponse({'pending': data})


@login_required
def chat_approve_member(request, room_id, user_id):
    """A'zoni tasdiqlash (faqat admin, POST)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    room = get_object_or_404(ChatRoom, pk=room_id)
    if not ChatAdmin.objects.filter(neighborhood=room.neighborhood, user=request.user).exists():
        return JsonResponse({'error': 'Ruxsat yo\'q'}, status=403)
    updated = ChatMember.objects.filter(room=room, user__id=user_id).update(
        is_approved=True, is_banned=False, approved_at=timezone.now()
    )
    return JsonResponse({'ok': bool(updated)})


@login_required
def chat_kick_member(request, room_id, user_id):
    """A'zoni ban qilish (faqat admin, POST)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    room = get_object_or_404(ChatRoom, pk=room_id)
    if not ChatAdmin.objects.filter(neighborhood=room.neighborhood, user=request.user).exists():
        return JsonResponse({'error': 'Ruxsat yo\'q'}, status=403)
    ChatMember.objects.filter(room=room, user__id=user_id).update(
        is_banned=True, is_approved=False
    )
    return JsonResponse({'ok': True})


@login_required
def chat_delete_message(request, room_id, msg_id):
    """Xabar o'chirish (faqat admin, POST)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    room = get_object_or_404(ChatRoom, pk=room_id)
    if not ChatAdmin.objects.filter(neighborhood=room.neighborhood, user=request.user).exists():
        return JsonResponse({'error': 'Ruxsat yo\'q'}, status=403)
    try:
        msg = ChatMessage.objects.get(pk=msg_id, room=room)
        msg.delete()
        return JsonResponse({'ok': True})
    except ChatMessage.DoesNotExist:
        return JsonResponse({'error': 'Xabar topilmadi'}, status=404)


@login_required
def chat_upload_image(request, room_id):
    """Admin rasm yuklash (POST multipart)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    room = get_object_or_404(ChatRoom, pk=room_id)
    if not ChatAdmin.objects.filter(neighborhood=room.neighborhood, user=request.user).exists():
        return JsonResponse({'error': 'Ruxsat yo\'q'}, status=403)

    image = request.FILES.get('image')
    caption = request.POST.get('caption', '').strip()[:500]
    if not image:
        return JsonResponse({'error': 'Rasm yuklanmadi'}, status=400)

    try:
        validate_file_type(image)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

    msg = ChatMessage.objects.create(
        room=room,
        user=request.user,
        text=caption,
        image=image,
        is_admin_message=True,
    )
    return JsonResponse({
        'ok': True,
        'message_id': str(msg.pk),
        'image_url': msg.image.url,
        'time': timezone.localtime(msg.created_at).strftime('%H:%M'),
    })


# ───────── CHAT API (JSON) — xabarlar ro'yxati ─────────
@login_required
def chat_messages_api(request, room_id):
    """Oxirgi xabarlarni JSON formatda qaytaradi"""
    room = get_object_or_404(ChatRoom, pk=room_id)
    is_admin = ChatAdmin.objects.filter(
        neighborhood=room.neighborhood, user=request.user
    ).exists()

    msgs = room.messages.select_related('user').order_by('-created_at')
    before_id = request.GET.get('before')
    after_id = request.GET.get('after_id')

    if before_id:
        try:
            before_msg = ChatMessage.objects.get(pk=before_id)
            msgs = msgs.filter(created_at__lt=before_msg.created_at)
        except ChatMessage.DoesNotExist:
            pass
    elif after_id:
        try:
            after_msg = ChatMessage.objects.get(pk=after_id)
            msgs = room.messages.select_related('user').filter(
                created_at__gt=after_msg.created_at
            ).order_by('created_at')
            return JsonResponse({'messages': [
                _serialize_msg(m, request.user, is_admin) for m in msgs
            ], 'has_more': False})
        except ChatMessage.DoesNotExist:
            pass

    msgs = list(msgs[:40])
    msgs.reverse()
    return JsonResponse({'messages': [
        _serialize_msg(m, request.user, is_admin) for m in msgs
    ], 'has_more': len(msgs) == 40})


def _serialize_msg(m, current_user, current_user_is_admin):
    from django.utils import timezone as tz
    if m.is_admin_message:
        display_name = '🛡️ Admin'
        initials = 'AD'
        user_id = 'admin'
    else:
        display_name = m.user.name or m.user.phone
        name_parts = display_name.split()
        initials = (name_parts[0][0] + name_parts[1][0]).upper() if len(name_parts) >= 2 else display_name[:2].upper()
        user_id = str(m.user.id)
    return {
        'id': str(m.pk),
        'text': m.text,
        'image_url': m.image.url if m.image else None,
        'user_id': user_id,
        'user_name': display_name,
        'user_initials': initials,
        'is_own': m.user == current_user,
        'is_admin': m.is_admin_message,
        'can_delete': current_user_is_admin,
        'time': tz.localtime(m.created_at).strftime('%H:%M'),
        'date': tz.localtime(m.created_at).strftime('%d.%m.%Y'),
    }


# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# VENUE BOOKING + PAYMENT VIEWS
# ══════════════════════════════════════════════════════════════════════════════

PLATFORM_COMMISSION = 0.10  # 10%

CANCELLATION_RULES = {
    # policy: [(days_before, refund_percent), ...]  — eng katta kundan tekshiriladi
    'flexible': [(1, 100), (0, 0)],
    'moderate': [(3, 50),  (0, 0)],
    'strict':   [(7, 25),  (0, 0)],
}


def _calc_refund(booking, cancelled_by):
    """
    Bekor qilish paytida mijozga qaytariladigan summa va jarima hisoblab qaytaradi.
    Egasi bekor qilsa: 100% qaytarish, komisiya platformada qoladi.
    """
    total = booking.total_amount or 0
    if cancelled_by == 'owner':
        return total, 0  # refund, penalty

    # Mijoz bekor qilsa — cancellation policy ishlaydi
    if booking.start_date:
        from datetime import date
        days_left = (booking.start_date - date.today()).days
    else:
        days_left = 0

    policy = booking.ad.cancellation_policy
    rules = CANCELLATION_RULES.get(policy, CANCELLATION_RULES['moderate'])
    refund_pct = 0
    for days_threshold, pct in rules:
        if days_left >= days_threshold:
            refund_pct = pct
            break

    refund = int(total * refund_pct / 100)
    penalty = total - refund
    return refund, penalty


@login_required
def booking_create(request, pk):
    """Venue bron so'rovi + mock to'lov."""
    ad = get_object_or_404(Ad, pk=pk, status='active')

    if not ad.venue_booking_enabled:
        messages.error(request, "Bu e'lon uchun bron tizimi mavjud emas.")
        return redirect('ad_detail', pk=pk)

    if ad.user == request.user:
        messages.error(request, "O'z e'loningizni bron qila olmaysiz.")
        return redirect('ad_detail', pk=pk)

    existing = Booking.objects.filter(
        ad=ad, buyer=request.user
    ).exclude(status='cancelled').first()

    if existing:
        messages.warning(request, "Siz bu e'lonni allaqachon bron qilgansiz.")
        return redirect('ad_detail', pk=pk)

    if request.method == 'POST':
        from datetime import date, datetime
        from django.utils import timezone as tz

        msg        = request.POST.get('message', '').strip()
        start_date = request.POST.get('start_date', '').strip()
        end_date   = request.POST.get('end_date', '').strip()
        guests_raw = request.POST.get('guests', '1')

        try:
            guests = max(1, int(guests_raw))
        except ValueError:
            guests = 1

        if not start_date or not end_date:
            messages.error(request, "Iltimos, boshlanish va tugash sanasini kiriting.")
            return redirect('ad_detail', pk=pk)

        try:
            sd = datetime.strptime(start_date, '%Y-%m-%d').date()
            ed = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Sana formati noto'g'ri.")
            return redirect('ad_detail', pk=pk)

        if sd < date.today():
            messages.error(request, "Boshlanish sanasi bugundan oldin bo'lishi mumkin emas.")
            return redirect('ad_detail', pk=pk)
        if sd >= ed:
            messages.error(request, "Tugash sanasi boshlanish sanasidan keyin bo'lishi kerak.")
            return redirect('ad_detail', pk=pk)

        overlap = Booking.objects.filter(
            ad=ad,
            status__in=['pending', 'confirmed'],
            start_date__lt=ed,
            end_date__gt=sd,
        ).exists()
        if overlap:
            messages.error(request, "Bu sanalar band. Boshqa sana tanlang.")
            return redirect('ad_detail', pk=pk)

        # Narx hisoblash
        days = (ed - sd).days
        if ad.venue_price_per_day:
            total = ad.venue_price_per_day * days
        elif ad.price:
            total = int(ad.price) * days
        else:
            total = 0

        platform_fee = int(total * PLATFORM_COMMISSION)
        owner_amount = total - platform_fee

        # Mock to'lov — darhol "held" holatiga o'tadi
        booking = Booking.objects.create(
            ad=ad,
            buyer=request.user,
            owner=ad.user,
            message=msg,
            guests=guests,
            start_date=sd,
            end_date=ed,
            total_amount=total,
            platform_fee=platform_fee,
            owner_amount=owner_amount,
            payment_status='held',
            paid_at=tz.now(),
        )

        messages.success(request, f"Bron so'rovingiz yuborildi! {total:,} so'm platformada ushlab turildi.")
        return redirect('booking_detail', booking_id=booking.pk)

    return redirect('ad_detail', pk=pk)


@login_required
def my_bookings(request):
    """Foydalanuvchi yuborgan bronlar."""
    from django.core.paginator import Paginator
    status_filter = request.GET.get('status', 'all')
    bookings = Booking.objects.filter(
        buyer=request.user
    ).select_related('ad', 'owner').prefetch_related('ad__images')

    if status_filter != 'all':
        bookings = bookings.filter(status=status_filter)

    paginator = Paginator(bookings, 15)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'my_bookings.html', {
        'bookings': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
    })


@login_required
def received_bookings(request):
    """E'lon egasiga kelgan bronlar."""
    from django.core.paginator import Paginator
    status_filter = request.GET.get('status', 'all')
    bookings = Booking.objects.filter(
        owner=request.user
    ).select_related('ad', 'buyer').prefetch_related('ad__images')

    if status_filter != 'all':
        bookings = bookings.filter(status=status_filter)

    pending_count = Booking.objects.filter(owner=request.user, status='pending').count()

    paginator = Paginator(bookings, 15)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'received_bookings.html', {
        'bookings': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'pending_count': pending_count,
    })


@login_required
def booking_action(request, booking_id, action):
    """Bronni tasdiqlash / bekor qilish / yakunlash — to'lov mantiq bilan."""
    from django.utils import timezone as tz

    booking = get_object_or_404(Booking, pk=booking_id)

    if action in ('confirm', 'complete'):
        if booking.owner != request.user:
            messages.error(request, "Ruxsat yo'q.")
            return redirect('received_bookings')
    elif action == 'cancel':
        if booking.owner != request.user and booking.buyer != request.user:
            messages.error(request, "Ruxsat yo'q.")
            return redirect('my_bookings')

    if request.method == 'POST':
        # ── TASDIQLASH ──────────────────────────────────────────
        if action == 'confirm' and booking.status == 'pending':
            booking.status = 'confirmed'
            booking.save(update_fields=['status', 'updated_at'])
            messages.success(request, "Bron tasdiqlandi! Mijoz xabardor qilindi.")
            return redirect('received_bookings')

        # ── BEKOR QILISH ─────────────────────────────────────────
        elif action == 'cancel' and booking.status in ('pending', 'confirmed'):
            cancelled_by = 'owner' if booking.owner == request.user else 'buyer'
            refund, penalty = _calc_refund(booking, cancelled_by)

            booking.status         = 'cancelled'
            booking.cancelled_by   = cancelled_by
            booking.refund_amount  = refund
            booking.penalty_amount = penalty

            if booking.payment_status == 'held':
                if refund == (booking.total_amount or 0):
                    booking.payment_status = 'refunded'
                elif refund > 0:
                    booking.payment_status = 'partial_refund'
                else:
                    booking.payment_status = 'released'

            booking.save()

            if cancelled_by == 'owner':
                msg = f"Bron bekor qilindi. Mijozga {refund:,} so'm qaytarildi."
            else:
                if penalty > 0:
                    msg = f"Bron bekor qilindi. {refund:,} so'm qaytarildi, {penalty:,} so'm jarima ushlab qolindi."
                else:
                    msg = f"Bron bekor qilindi. {refund:,} so'm to'liq qaytarildi."

            messages.success(request, msg)
            if booking.owner == request.user:
                return redirect('received_bookings')
            return redirect('my_bookings')

        # ── YAKUNLASH ────────────────────────────────────────────
        elif action == 'complete' and booking.status == 'confirmed':
            booking.status         = 'completed'
            booking.payment_status = 'released'
            booking.save(update_fields=['status', 'payment_status', 'updated_at'])
            messages.success(
                request,
                f"Bron yakunlandi! {booking.owner_amount:,} so'm egaga o'tkazildi, "
                f"{booking.platform_fee:,} so'm komissiya platformada qoldi."
            )
            return redirect('received_bookings')

    messages.error(request, "Noto'g'ri amal.")
    return redirect('received_bookings')


@login_required
def booking_detail(request, booking_id):
    """Bron tafsilotlari."""
    booking = get_object_or_404(Booking, pk=booking_id)

    if booking.buyer != request.user and booking.owner != request.user:
        messages.error(request, "Ruxsat yo'q.")
        return redirect('my_bookings')

    return render(request, 'booking_detail.html', {'booking': booking})


# ═══════════════════════════════════════════════════════════════════════════════
# ─── ISH E'LONLARI (JobAd) ─────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
def job_list(request):
    from django.db.models import Q
    from django.core.paginator import Paginator

    query = request.GET.get('q', '').strip()
    job_type_filter = request.GET.get('job_type', 'all')

    jobs = JobAd.objects.filter(status='active').select_related('user')

    if query:
        jobs = jobs.filter(
            Q(title__icontains=query) |
            Q(company__icontains=query) |
            Q(description__icontains=query) |
            Q(location__icontains=query)
        )

    if job_type_filter != 'all':
        jobs = jobs.filter(job_type=job_type_filter)

    paginator = Paginator(jobs, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'job_list.html', {
        'jobs': page_obj,
        'page_obj': page_obj,
        'query': query,
        'job_type_filter': job_type_filter,
        'job_types': JobAd.JOB_TYPE_CHOICES,
    })


def job_detail(request, pk):
    job = get_object_or_404(JobAd, pk=pk)
    session_key = f'viewed_job_{pk}'
    if not request.session.get(session_key):
        job.views += 1
        job.save(update_fields=['views'])
        request.session[session_key] = True
    return render(request, 'job_detail.html', {'job': job})


@login_required
def job_create(request):
    if request.method == 'POST':
        title        = request.POST.get('title', '').strip()
        company      = request.POST.get('company', '').strip()
        company_description = request.POST.get('company_description', '').strip()
        manager_name = request.POST.get('manager_name', '').strip()
        manager_phone = request.POST.get('manager_phone', '').strip()
        job_type     = request.POST.get('job_type', 'full_time')
        location     = request.POST.get('location', '').strip()
        description  = request.POST.get('description', '').strip()
        requirements = request.POST.get('requirements', '').strip()
        deadline     = request.POST.get('deadline') or None
        salary_min   = request.POST.get('salary_min') or None
        salary_max   = request.POST.get('salary_max') or None
        contact_phone    = request.POST.get('contact_phone', '').strip()
        contact_telegram = request.POST.get('contact_telegram', '').strip()

        if not title or not company or not description:
            messages.error(request, "Sarlavha, kompaniya va tavsif majburiy.")
            return render(request, 'job_form.html', {
                'mode': 'create',
                'post': _form_post(request),
                'job_types': JobAd.JOB_TYPE_CHOICES,
            })

        def parse_int(val):
            try:
                return int(str(val).replace(' ', '').replace(',', ''))
            except (ValueError, TypeError):
                return None

        job = JobAd.objects.create(
            user=request.user,
            title=title,
            company=company,
            company_description=company_description,
            manager_name=manager_name,
            manager_phone=manager_phone,
            job_type=job_type,
            location=location,
            description=description,
            requirements=requirements,
            deadline=deadline,
            salary_min=parse_int(salary_min),
            salary_max=parse_int(salary_max),
            contact_phone=contact_phone,
            contact_telegram=contact_telegram,
        )
        messages.success(request, "Ish e'loni muvaffaqiyatli joylandi!")
        return redirect('job_detail', pk=job.pk)

    return render(request, 'job_form.html', {
        'mode': 'create',
        'job_types': JobAd.JOB_TYPE_CHOICES,
    })


@login_required
def job_edit(request, pk):
    job = get_object_or_404(JobAd, pk=pk)
    if job.user != request.user:
        messages.error(request, "Bu e'lonni tahrirlash huquqingiz yo'q.")
        return redirect('job_detail', pk=pk)

    if request.method == 'POST':
        job.title        = request.POST.get('title', '').strip()
        job.company      = request.POST.get('company', '').strip()
        job.company_description = request.POST.get('company_description', '').strip()
        job.manager_name = request.POST.get('manager_name', '').strip()
        job.manager_phone = request.POST.get('manager_phone', '').strip()
        job.job_type     = request.POST.get('job_type', job.job_type)
        job.location     = request.POST.get('location', '').strip()
        job.description  = request.POST.get('description', '').strip()
        job.requirements = request.POST.get('requirements', '').strip()
        job.deadline     = request.POST.get('deadline') or None
        job.status       = request.POST.get('status', job.status)
        job.contact_phone    = request.POST.get('contact_phone', '').strip()
        job.contact_telegram = request.POST.get('contact_telegram', '').strip()

        def parse_int(val):
            try:
                return int(str(val).replace(' ', '').replace(',', ''))
            except (ValueError, TypeError):
                return None

        job.salary_min = parse_int(request.POST.get('salary_min') or None)
        job.salary_max = parse_int(request.POST.get('salary_max') or None)

        if not job.title or not job.company or not job.description:
            messages.error(request, "Sarlavha, kompaniya va tavsif majburiy.")
            return render(request, 'job_form.html', {
                'mode': 'edit', 'job': job,
                'job_types': JobAd.JOB_TYPE_CHOICES,
                'statuses': JobAd.STATUS_CHOICES,
            })

        job.save()
        messages.success(request, "Ish e'loni muvaffaqiyatli yangilandi!")
        return redirect('job_detail', pk=job.pk)

    return render(request, 'job_form.html', {
        'mode': 'edit',
        'job': job,
        'job_types': JobAd.JOB_TYPE_CHOICES,
        'statuses': JobAd.STATUS_CHOICES,
    })


@login_required
def job_delete(request, pk):
    job = get_object_or_404(JobAd, pk=pk)
    if job.user != request.user:
        messages.error(request, "Bu e'lonni o'chirish huquqingiz yo'q.")
        return redirect('job_detail', pk=pk)
    if request.method == 'POST':
        job.status = 'deleted'
        job.save(update_fields=['status'])
        messages.success(request, "Ish e'loni o'chirildi.")
        return redirect('job_list')
    return render(request, 'job_confirm_delete.html', {'job': job})


@login_required
def job_toggle_close(request, pk):
    job = get_object_or_404(JobAd, pk=pk)
    if job.user != request.user:
        messages.error(request, "Ruxsat yo'q.")
        return redirect('job_detail', pk=pk)
    if request.method == 'POST':
        job.status = 'active' if job.status == 'closed' else 'closed'
        job.save(update_fields=['status'])
        label = "Faol qilindi" if job.status == 'active' else "Yopildi"
        messages.success(request, f"Ish e'loni {label}.")
    return redirect('job_detail', pk=pk)


# ═══════════════════════════════════════════════════════════════════════════════
# ─── RESUME / ARIZA (ResumeAd) ─────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

def resume_list(request):
    from django.db.models import Q
    from django.core.paginator import Paginator

    query = request.GET.get('q', '').strip()
    exp_filter = request.GET.get('experience', 'all')

    resumes = ResumeAd.objects.filter(status='active').select_related('user')

    if query:
        resumes = resumes.filter(
            Q(title__icontains=query) |
            Q(skills__icontains=query) |
            Q(about__icontains=query) |
            Q(location__icontains=query)
        )

    if exp_filter != 'all':
        resumes = resumes.filter(experience=exp_filter)

    paginator = Paginator(resumes, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'resume_list.html', {
        'resumes': page_obj,
        'page_obj': page_obj,
        'query': query,
        'exp_filter': exp_filter,
        'experience_choices': ResumeAd.EXP_CHOICES,
    })


def resume_detail(request, pk):
    resume = get_object_or_404(ResumeAd, pk=pk)
    session_key = f'viewed_resume_{pk}'
    if not request.session.get(session_key):
        resume.views += 1
        resume.save(update_fields=['views'])
        request.session[session_key] = True
    return render(request, 'resume_detail.html', {'resume': resume})


@login_required
def resume_create(request):
    if request.method == 'POST':
        title       = request.POST.get('title', '').strip()
        experience  = request.POST.get('experience', 'no_exp')
        location    = request.POST.get('location', '').strip()
        skills      = request.POST.get('skills', '').strip()
        about       = request.POST.get('about', '').strip()
        salary_min  = request.POST.get('salary_min') or None
        contact_phone    = request.POST.get('contact_phone', '').strip()
        contact_telegram = request.POST.get('contact_telegram', '').strip()

        if not title or not about:
            messages.error(request, "Kasb nomi va o'zi haqida matn majburiy.")
            return render(request, 'resume_form.html', {
                'mode': 'create',
                'post': _form_post(request),
                'experience_choices': ResumeAd.EXP_CHOICES,
            })

        def parse_int(val):
            try:
                return int(str(val).replace(' ', '').replace(',', ''))
            except (ValueError, TypeError):
                return None

        resume = ResumeAd.objects.create(
            user=request.user,
            title=title,
            experience=experience,
            location=location,
            skills=skills,
            about=about,
            salary_min=parse_int(salary_min),
            contact_phone=contact_phone,
            contact_telegram=contact_telegram,
        )
        messages.success(request, "Resume muvaffaqiyatli joylandi!")
        return redirect('resume_detail', pk=resume.pk)

    return render(request, 'resume_form.html', {
        'mode': 'create',
        'post': _form_post(request),
        'experience_choices': ResumeAd.EXP_CHOICES,
    })


@login_required
def resume_edit(request, pk):
    resume = get_object_or_404(ResumeAd, pk=pk)
    if resume.user != request.user:
        messages.error(request, "Bu resumeni tahrirlash huquqingiz yo'q.")
        return redirect('resume_detail', pk=pk)

    if request.method == 'POST':
        resume.title      = request.POST.get('title', '').strip()
        resume.experience = request.POST.get('experience', resume.experience)
        resume.location   = request.POST.get('location', '').strip()
        resume.skills     = request.POST.get('skills', '').strip()
        resume.about      = request.POST.get('about', '').strip()
        resume.status     = request.POST.get('status', resume.status)
        resume.contact_phone    = request.POST.get('contact_phone', '').strip()
        resume.contact_telegram = request.POST.get('contact_telegram', '').strip()

        def parse_int(val):
            try:
                return int(str(val).replace(' ', '').replace(',', ''))
            except (ValueError, TypeError):
                return None

        resume.salary_min = parse_int(request.POST.get('salary_min') or None)

        if not resume.title or not resume.about:
            messages.error(request, "Kasb nomi va o'zi haqida matn majburiy.")
            return render(request, 'resume_form.html', {
                'mode': 'edit', 'resume': resume, 'post': _form_post(request),
                'experience_choices': ResumeAd.EXP_CHOICES,
                'statuses': ResumeAd.STATUS_CHOICES,
            })

        resume.save()
        messages.success(request, "Resume muvaffaqiyatli yangilandi!")
        return redirect('resume_detail', pk=resume.pk)

    return render(request, 'resume_form.html', {
        'mode': 'edit',
        'resume': resume,
        'post': _form_post(request),
        'experience_choices': ResumeAd.EXP_CHOICES,
        'statuses': ResumeAd.STATUS_CHOICES,
    })


@login_required
def resume_delete(request, pk):
    resume = get_object_or_404(ResumeAd, pk=pk)
    if resume.user != request.user:
        messages.error(request, "Bu resumeni o'chirish huquqingiz yo'q.")
        return redirect('resume_detail', pk=pk)
    if request.method == 'POST':
        resume.status = 'deleted'
        resume.save(update_fields=['status'])
        messages.success(request, "Resume o'chirildi.")
        return redirect('resume_list')
    return render(request, 'resume_confirm_delete.html', {'resume': resume})


@login_required
def resume_toggle_hired(request, pk):
    resume = get_object_or_404(ResumeAd, pk=pk)
    if resume.user != request.user:
        messages.error(request, "Ruxsat yo'q.")
        return redirect('resume_detail', pk=pk)
    if request.method == 'POST':
        if resume.status == 'hired':
            resume.status = 'active'
            messages.success(request, "Resume yana faol holatga qaytarildi.")
        else:
            resume.status = 'hired'
            messages.success(request, "Tabriklaymiz! Ishga joylashgansiz deb belgilandi.")
        resume.save(update_fields=['status'])
    return redirect('resume_detail', pk=pk)


# ─── KOMMUNAL TO'LOVLAR ──────────────────────────────────────────────────────

from django.db.models import Sum, Count
import datetime

@login_required
def utility_list(request):
    payments = UtilityPayment.objects.filter(user=request.user)

    # Filtrlar
    service_filter = request.GET.get('service', '')
    status_filter  = request.GET.get('status', '')
    period_filter  = request.GET.get('period', '')

    if service_filter:
        payments = payments.filter(service=service_filter)
    if status_filter:
        payments = payments.filter(status=status_filter)
    if period_filter:
        payments = payments.filter(period=period_filter)

    # Statistika
    total_paid = UtilityPayment.objects.filter(
        user=request.user, status='tolangan'
    ).aggregate(s=Sum('amount'))['s'] or 0

    this_month = datetime.date.today().strftime('%Y-%m')
    month_total = UtilityPayment.objects.filter(
        user=request.user, period=this_month
    ).aggregate(s=Sum('amount'))['s'] or 0

    pending_count = UtilityPayment.objects.filter(
        user=request.user, status='kutilmoqda'
    ).count()

    service_choices = UtilityPayment.SERVICE_CHOICES
    status_choices  = UtilityPayment.STATUS_CHOICES

    return render(request, 'utility_list.html', {
        'payments':       payments,
        'total_paid':     total_paid,
        'month_total':    month_total,
        'pending_count':  pending_count,
        'service_choices': service_choices,
        'status_choices':  status_choices,
        'service_filter':  service_filter,
        'status_filter':   status_filter,
        'period_filter':   period_filter,
        'this_month':      this_month,
    })


@login_required
def utility_create(request):
    if request.method == 'POST':
        service  = request.POST.get('service')
        amount   = request.POST.get('amount')
        period   = request.POST.get('period')
        status   = request.POST.get('status', 'tolangan')
        note     = request.POST.get('note', '')
        paid_at  = request.POST.get('paid_at')

        if not all([service, amount, period, paid_at]):
            messages.error(request, "Barcha majburiy maydonlarni to'ldiring.")
            return redirect('utility_create')

        try:
            amount = int(amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            messages.error(request, "Summa musbat son bo'lishi kerak.")
            return redirect('utility_create')

        UtilityPayment.objects.create(
            user=request.user,
            service=service,
            amount=amount,
            period=period,
            status=status,
            note=note,
            paid_at=paid_at,
        )
        messages.success(request, "To'lov muvaffaqiyatli qo'shildi! ✅")
        return redirect('utility_list')

    today = datetime.date.today()
    this_month = today.strftime('%Y-%m')
    service_choices = UtilityPayment.SERVICE_CHOICES
    status_choices  = UtilityPayment.STATUS_CHOICES

    return render(request, 'utility_form.html', {
        'service_choices': service_choices,
        'status_choices':  status_choices,
        'today':           today.strftime('%Y-%m-%d'),
        'this_month':      this_month,
    })


@login_required
def utility_delete(request, pk):
    payment = get_object_or_404(UtilityPayment, pk=pk, user=request.user)
    if request.method == 'POST':
        payment.delete()
        messages.success(request, "To'lov o'chirildi.")
    return redirect('utility_list')


@login_required
def utility_edit(request, pk):
    payment = get_object_or_404(UtilityPayment, pk=pk, user=request.user)

    if request.method == 'POST':
        service = request.POST.get('service')
        amount  = request.POST.get('amount')
        period  = request.POST.get('period')
        status  = request.POST.get('status', payment.status)
        note    = request.POST.get('note', '')
        paid_at = request.POST.get('paid_at')

        if not all([service, amount, period, paid_at]):
            messages.error(request, "Barcha majburiy maydonlarni to'ldiring.")
            return redirect('utility_edit', pk=pk)

        try:
            amount = int(amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            messages.error(request, "Summa musbat son bo'lishi kerak.")
            return redirect('utility_edit', pk=pk)

        payment.service = service
        payment.amount  = amount
        payment.period  = period
        payment.status  = status
        payment.note    = note
        payment.paid_at = paid_at
        payment.save()
        messages.success(request, "To'lov muvaffaqiyatli yangilandi! ✅")
        return redirect('utility_list')

    today = datetime.date.today()
    return render(request, 'utility_edit.html', {
        'payment': payment,
        'service_choices': UtilityPayment.SERVICE_CHOICES,
        'status_choices':  UtilityPayment.STATUS_CHOICES,
        'today': today.strftime('%Y-%m-%d'),
    })


# ─── BUSINESS / TRANSPORT / COURSE / BOOST ───────────────────────────────
from django.db.models import Q, Avg

@login_required
def dashboard(request):
    """Yagona boshqaruv paneli — barcha faoliyat bir joyda (mavjud related manager lar orqali)."""
    u = request.user
    return render(request, 'dashboard.html', {
        'orders': u.delivery_orders.prefetch_related('items')[:10],
        'trips': u.taxi_trips.select_related('taxist')[:10],
        'venue_bookings': u.venue_bookings.select_related('venue')[:10],
        'stores': u.stores.select_related('category').all(),
        'venues': u.venues.all(),
        'resumes': u.resume_ads.all(),
        'ad_bookings': u.my_bookings.select_related('ad')[:10],
    })


from django.contrib.admin.views.decorators import staff_member_required


@staff_member_required
def admin_dashboard(request):
    """Phase 4 — boshqaruv analitikasi (faqat xodimlar uchun).

    ~16 ta COUNT/SUM so'rovi 60 soniya keshlanadi — panel tez-tez yangilanmaydi,
    shu sababli har ochilishda bazani urmaymiz.
    """
    from django.core.cache import cache
    ctx = cache.get('admin_dashboard_ctx')
    if ctx is None:
        ctx = _compute_admin_dashboard()
        cache.set('admin_dashboard_ctx', ctx, 60)  # 60s TTL
    return render(request, 'admin_dashboard.html', ctx)


def _compute_admin_dashboard():
    from django.db.models import Sum, Count
    from delivery.models import Store, Product, Order, DeliveryDriver
    from taxi.models import Trip
    from booking.models import Venue, VenueBooking
    from places.models import Place

    order_qs = Order.objects.all()
    status_counts = {row['status']: row['c'] for row in order_qs.values('status').annotate(c=Count('id'))}
    status_labels = dict(Order.STATUS_CHOICES)
    order_status = [{'label': status_labels.get(k, k), 'count': v} for k, v in status_counts.items()]

    delivery_rev = order_qs.filter(payment_status='paid').aggregate(s=Sum('total'))['s'] or 0
    taxi_rev = Trip.objects.filter(payment_status='paid').aggregate(s=Sum('price'))['s'] or 0
    try:
        from payments.models import ServicePayment
        svc_rev = ServicePayment.objects.filter(status='paid').aggregate(s=Sum('amount'))['s'] or 0
    except Exception:
        svc_rev = 0

    metrics = {
        'users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'stores': Store.objects.count(),
        'products': Product.objects.count(),
        'orders': order_qs.count(),
        'drivers': DeliveryDriver.objects.count(),
        'taxi_requests': Trip.objects.count(),
        'venues': Venue.objects.count(),
        'bookings': VenueBooking.objects.count(),
        'attractions': Place.objects.filter(category='tourist').count(),
        'places': Place.objects.count(),
        'ads': Ad.objects.count(),
    }
    revenue = {
        'delivery': delivery_rev, 'taxi': taxi_rev, 'services': svc_rev,
        'total': delivery_rev + taxi_rev + svc_rev,
    }
    module_chart = [
        ('Foydalanuvchi', metrics['users']), ('Do\'kon', metrics['stores']),
        ('Mahsulot', metrics['products']), ('Buyurtma', metrics['orders']),
        ('Haydovchi', metrics['drivers']), ('Taksi', metrics['taxi_requests']),
        ('Joy', metrics['venues']), ('Bron', metrics['bookings']),
        ('E\'lon', metrics['ads']), ('Xarita joy', metrics['places']),
    ]
    return {
        'metrics': metrics, 'revenue': revenue,
        'order_status': order_status, 'module_chart': module_chart,
    }


@login_required
def password_change_view(request):
    """Foydalanuvchi o'z parolini o'zgartirishi mumkin."""
    if request.method == 'POST':
        old_password = request.POST.get('old_password', '')
        new_password = request.POST.get('new_password', '').strip()
        confirm = request.POST.get('confirm_password', '').strip()

        if not request.user.check_password(old_password):
            messages.error(request, "Eski parol noto'g'ri.")
            return redirect('password_change')

        if len(new_password) < 6:
            messages.error(request, "Yangi parol kamida 6 ta belgidan iborat bo'lishi kerak.")
            return redirect('password_change')

        if new_password != confirm:
            messages.error(request, "Yangi parollar mos kelmaydi.")
            return redirect('password_change')

        request.user.set_password(new_password)
        request.user.save()
        login(request, request.user)  # session yangilash
        messages.success(request, "Parol muvaffaqiyatli o'zgartirildi! ✅")
        return redirect('profile')

    return render(request, 'password_change.html')




# ─── TASK 23: BOOST / FEATURED ────────────────────────────────────────────────

@login_required
def boost_ad_view(request, pk):
    ad = get_object_or_404(Ad, pk=pk, user=request.user)
    PLANS = {
        'week':    {'days': 7,  'amount': 10000,  'label': "7 kunlik — 10 000 so'm"},
        'month':   {'days': 30, 'amount': 30000,  'label': "30 kunlik — 30 000 so'm"},
        'quarter': {'days': 90, 'amount': 75000,  'label': "90 kunlik — 75 000 so'm"},
    }

    if request.method == 'POST':
        plan_key = request.POST.get('plan', '')
        if plan_key not in PLANS:
            messages.error(request, "Noto'g'ri plan tanlandi.")
            return redirect('boost_ad', pk=pk)

        plan = PLANS[plan_key]
        now = timezone.now()
        expires = now + timezone.timedelta(days=plan['days'])

        # Boost payment yaratish
        BoostPayment.objects.create(
            user=request.user,
            ad=ad,
            plan=plan_key,
            amount=plan['amount'],
            status='active',
            starts_at=now,
            expires_at=expires,
        )

        # E'lonni boost qilish
        ad.is_boosted = True
        ad.boosted_until = expires
        ad.save()

        messages.success(request, f"E'lon {plan['days']} kunga TOP ga chiqarildi! ✅")
        return redirect('ad_detail', pk=pk)

    # Joriy boost holati
    active_boost = BoostPayment.objects.filter(
        ad=ad, status='active', expires_at__gt=timezone.now()
    ).first()

    return render(request, 'boost_ad.html', {
        'ad': ad,
        'plans': PLANS,
        'active_boost': active_boost,
    })


def app_download(request):
    """Mobil ilovani yuklab olish sahifasi."""
    return render(request, 'app_download.html')
