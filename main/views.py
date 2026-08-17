from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.conf import settings as _django_settings
from django.utils.http import url_has_allowed_host_and_scheme
from datetime import timedelta
import random
import string
from django.core.paginator import Paginator
from django.db.models import Count, F, Q, Sum
from .models import Ad, AdImage, User, JobAd, ResumeAd, UtilityPayment, BoostPayment, OTPCode
import logging
from .utils import validate_file_type, clean_image, ratelimit
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
    cart_ad_ids = set()
    if request.user.is_authenticated:
        from .models import AdFavorite
        page_pks = [a.pk for a in page_obj]
        fav_ids = set(AdFavorite.objects.filter(
            user=request.user, ad__in=page_pks
        ).values_list('ad_id', flat=True))
        from delivery.models import CartAd, get_active_cart
        cart = get_active_cart(request.user)
        cart_ad_ids = set(CartAd.objects.filter(
            cart=cart, ad__in=page_pks
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
        'cart_ad_ids': cart_ad_ids,
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
            # OTP tasdiqlandi — parol tekshirilmaydi, shuning uchun `authenticate()`
            # chaqirilmaydi va `user.backend` o'rnatilmagan bo'ladi. Bir nechta
            # AUTHENTICATION_BACKENDS sozlangani uchun Django qaysi backend
            # ishlatilganini o'zi aniqlay olmaydi va ValueError beradi —
            # backend'ni ANIQ ko'rsatish SHART.
            login(request, user, backend='main.auth_backends.PhoneModelBackend')
            request.session.pop('pending_phone', None)
            messages.success(request, "Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!")
            return redirect('profile')
        else:
            otp.attempts += 1
            otp.save(update_fields=['attempts'])
            remaining = max(0, OTP_MAX_ATTEMPTS - otp.attempts)
            messages.error(request, f"Tasdiqlash kodi xato. Qolgan urinishlar: {remaining}.")

    return render(request, 'registration/verify_otp.html', {'phone': phone})


def _post_login_target(user):
    """Kirishdan keyin qayerga tushadi — roliga qarab.

    Kuryer uchun bosh sahifa/profil emas, ish paneli: u saytga e'lon o'qish
    uchun emas, buyurtma olish uchun kiradi (main/roles.py).
    """
    from .roles import is_courier
    return 'delivery:driver_dashboard' if is_courier(user) else 'profile'


@login_required
def after_login(request):
    """LOGIN_REDIRECT_URL manzili — rolga qarab taqsimlaydi.

    `/accounts/login/` (django.contrib.auth.urls) o'z view'iga ega va bizning
    `user_login` mantig'idan o'tmaydi; yagona taqsimlagich shu yerda.
    """
    return redirect(_post_login_target(request.user))


@ratelimit('login', limit=10, window=300, methods=('POST',))
def user_login(request):
    if request.user.is_authenticated:
        return redirect(_post_login_target(request.user))

    if request.method == 'POST':
        phone = request.POST.get('phone') or request.POST.get('username')
        password = request.POST.get('password')

        # Telefon format variantlarini PhoneModelBackend hal qiladi
        # (main/auth_backends.py) — bu yerda faqat backendga uzatamiz.
        user = authenticate(request, username=phone, password=password)

        if user is not None:
            login(request, user)
            return redirect(_post_login_target(user))
        else:
            logger.warning("Failed login: phone=%s ip=%s", phone, request.META.get('REMOTE_ADDR'))
            messages.error(request, "Telefon raqami yoki parol xato.")

    return render(request, 'registration/login.html', {'mode': 'login'})


@login_required
def profile(request):
    # O'chirilgan e'lonlar profilda ko'rinmasligi ham, sanalmasligi ham kerak.
    user_ads = request.user.ads.exclude(status='deleted').prefetch_related('images')
    ads_count = user_ads.count()
    total_views = user_ads.aggregate(t=Sum('views'))['t'] or 0
    return render(request, 'profile.html', {
        'ads': user_ads,
        'ads_count': ads_count,
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

        # Jins va tug'ilgan sana (reklama auditoriyasi uchun — ixtiyoriy).
        gender = request.POST.get('gender', '')
        if gender in ('', 'male', 'female'):
            user.gender = gender
        birth_date = request.POST.get('birth_date', '').strip()
        if 'birth_date' in request.POST:
            user.birth_date = birth_date or None

        if password:
            user.set_password(password)

        if avatar:
            try:
                user.avatar = clean_image(avatar, 'portrait')
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

    from .models import AdFavorite, AdReport, AdInquiry
    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = AdFavorite.objects.filter(ad=ad, user=request.user).exists()
    # Egasi — kelgan barcha savollarni, xaridor esa FAQAT o'zi yozganlarini
    # ko'radi (ilgari xaridorga hech narsa ko'rsatilmasdi, shu bois o'z
    # xabarini o'chirish ham imkonsiz edi).
    inquiries = None
    my_inquiries = None
    if request.user.is_authenticated:
        if request.user.id == ad.user_id:
            inquiries = ad.inquiries.select_related('sender')
        else:
            my_inquiries = ad.inquiries.filter(sender=request.user)

    return render(request, 'ad_detail.html', {
        'ad': ad,
        'is_favorite': is_favorite,
        'report_reasons': AdReport.REASON_CHOICES,
        'inquiries': inquiries,
        'my_inquiries': my_inquiries,
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


def _back_or(request, fallback, **kwargs):
    """Kelgan sahifaga qaytaradi; faqat shu saytga bo'lsa (ochiq redirect himoyasi)."""
    nxt = request.POST.get('next') or request.META.get('HTTP_REFERER', '')
    if nxt and url_has_allowed_host_and_scheme(
            nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(nxt)
    return redirect(fallback, **kwargs)


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
        )

        for i, img in enumerate(images[:10]):
            try:
                AdImage.objects.create(ad=ad, image=clean_image(img), order=i)
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

        price = request.POST.get('price', None)
        if ad.price_type not in ('fixed', 'free'):
            ad.price_type = 'fixed'
        if ad.price_type == 'fixed':
            if not price or not str(price).strip():
                messages.error(request, "Belgilangan narx turi uchun narx kiritish majburiy.")
                return render(request, 'ad_form.html', {
                    'mode': 'edit', 'ad': ad, 'post': _form_post(request),
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
                    'mode': 'edit', 'ad': ad, 'post': _form_post(request),
                    'categories': Ad.CATEGORY_CHOICES,
                    'price_types': Ad.PRICE_TYPE_CHOICES,
                    'statuses': Ad.STATUS_CHOICES,
                })
        else:
            ad.price = None

        if not ad.title or not ad.category:
            messages.error(request, "Sarlavha va kategoriya majburiy.")
            return render(request, 'ad_form.html', {
                'mode': 'edit', 'ad': ad, 'post': _form_post(request),
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
                AdImage.objects.create(ad=ad, image=clean_image(img), order=existing_count + i)
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
        return redirect('my_ads')

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

    # Ro'yxatdan belgilangan bo'lsa — ro'yxatga qaytaramiz. Avval har safar
    # e'lon sahifasiga otib yuborardi va foydalanuvchi joyini yo'qotardi.
    return _back_or(request, 'ad_detail', pk=pk)


# ───────── E'LONLARIM (alohida sahifa) ─────────
@login_required
def my_ads(request):
    status_filter = request.GET.get('status', 'all')
    base = request.user.ads.exclude(status='deleted')

    # Statistika har doim to'liq ro'yxat bo'yicha — tab filtri unga ta'sir qilmasin.
    stats = base.aggregate(
        active=Count('pk', filter=Q(status='active')),
        sold=Count('pk', filter=Q(status='sold')),
        views=Sum('views'),
    )

    ads = base.prefetch_related('images')
    if status_filter != 'all':
        ads = ads.filter(status=status_filter)
    paginator = Paginator(ads, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'my_ads.html', {
        'ads': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': page_obj.has_other_pages(),
        'status_filter': status_filter,
        'statuses': Ad.STATUS_CHOICES,
        'active_count': stats['active'],
        'sold_count': stats['sold'],
        'total_views': stats['views'] or 0,
    })




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
        # Taksi arxivlangan — TAXI_ENABLED=False bo'lsa sayohatlar so'ralmaydi.
        'trips': (u.taxi_trips.select_related('taxist')[:10]
                  if _django_settings.TAXI_ENABLED else []),
        'venue_bookings': u.venue_bookings.select_related('venue')[:10],
        'stores': u.stores.select_related('category').all(),
        'venues': u.venues.all(),
        'resumes': u.resume_ads.all(),
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
        # Amaldagi boost tugamagan bo'lsa — yangisi uning ustiga qo'shiladi.
        # Aks holda qolgan kunlar yonib ketardi: 90 kunlik ustiga 7 kunlik
        # olish `boosted_until` ni +90 dan +7 ga TUSHIRARDI.
        starts = now
        if ad.is_boosted and ad.boosted_until and ad.boosted_until > now:
            starts = ad.boosted_until
        expires = starts + timezone.timedelta(days=plan['days'])

        # Boost payment yaratish
        BoostPayment.objects.create(
            user=request.user,
            ad=ad,
            plan=plan_key,
            amount=plan['amount'],
            status='active',
            starts_at=starts,
            expires_at=expires,
        )

        # E'lonni boost qilish
        ad.is_boosted = True
        ad.boosted_until = expires
        ad.save()

        if starts > now:
            messages.success(
                request,
                f"Boost {plan['days']} kunga uzaytirildi — "
                f"{timezone.localtime(expires):%d.%m.%Y} gacha TOP da. ✅")
        else:
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


def download_apk(request):
    """APK'ni to'g'ridan-to'g'ri (SIQISHSIZ) uzatadi.

    DIQQAT: /static/samcity.apk orqali WhiteNoise (CompressedStaticFilesStorage)
    APK'ni gzip qilib buzib yuboradi (55MB → ~23MB, Android o'rnata olmaydi).
    Shu view WhiteNoise'ni chetlab o'tib, faylni to'liq va to'g'ri Content-Type
    bilan beradi.
    """
    import os
    from django.conf import settings
    from django.http import FileResponse, Http404

    candidates = [
        os.path.join(settings.BASE_DIR, 'main', 'static', 'samcity.apk'),
        os.path.join(settings.STATIC_ROOT, 'samcity.apk'),
    ]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if not path:
        raise Http404("APK topilmadi. Iltimos keyinroq urinib ko'ring.")

    resp = FileResponse(
        open(path, 'rb'),
        content_type='application/vnd.android.package-archive',
    )
    resp['Content-Length'] = os.path.getsize(path)
    resp['Content-Disposition'] = 'attachment; filename="samcity.apk"'
    # WhiteNoise/prokси gzip qo'shmasligi uchun
    resp['Content-Encoding'] = 'identity'
    resp['Cache-Control'] = 'public, max-age=3600'
    return resp
