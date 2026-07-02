from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from main.utils import validate_file_type
from .models import (
    DeliveryCategory, Store, StoreImage, Product, ProductImage, Cart, Order, OrderItem,
    DeliveryDriver, DriverLocation, StoreUpdate, StoreSubscription,
    StoreChatThread, StoreChatMessage, can_transition,
)
from .feed import create_store_update
from .chat import get_or_create_thread, is_participant, create_message
from .realtime import (
    push_driver_location_for_orders, push_order_status, ACTIVE_DELIVERY_STATUSES,
)
from main.utils import ratelimit


DELIVERY_FEE = 10000  # belgilangan yetkazish narxi (so'm)


def _card_brand(digits):
    if digits.startswith('8600'):
        return 'Uzcard'
    if digits.startswith('9860'):
        return 'Humo'
    if digits.startswith('4'):
        return 'Visa'
    if digits.startswith('5'):
        return 'Mastercard'
    return 'Karta'


# ── Store views ───────────────────────────────────────────────────────────────

def store_list_view(request):
    qs = Store.objects.filter(is_active=True).select_related('owner', 'category')

    q = request.GET.get('q', '').strip()
    cat_slug = request.GET.get('cat', '').strip()

    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(address__icontains=q)
        )
    if cat_slug:
        qs = qs.filter(category__slug=cat_slug)

    categories = DeliveryCategory.objects.all()

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'delivery/store_list.html', {
        'stores': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': paginator.num_pages > 1,
        'categories': categories,
        'q': q,
        'cat_slug': cat_slug,
    })


def store_detail_view(request, pk):
    store = get_object_or_404(
        Store.objects.select_related('owner', 'category'),
        pk=pk,
        is_active=True,
    )

    # Product search within this store
    pq = request.GET.get('pq', '').strip()
    products_qs = (
        Product.objects
        .filter(store=store, is_available=True)
        .prefetch_related('images')
    )
    if pq:
        products_qs = products_qs.filter(
            Q(name__icontains=pq) | Q(description__icontains=pq)
        )

    is_subscribed = False
    if request.user.is_authenticated:
        is_subscribed = StoreSubscription.objects.filter(
            store=store, user=request.user, is_enabled=True).exists()

    return render(request, 'delivery/store_detail.html', {
        'store': store,
        'products': products_qs,
        'pq': pq,
        # Savatga qo'shish tugmasi: pickup yoqilgan do'konda (yoki global flag)
        # ko'rinadi. Pickup rejimida bu — "oldindan to'lab, o'zi olib ketish".
        'cart_enabled': store.pickup_enabled or settings.DELIVERY_CART_ENABLED,
        'pickup_mode': store.pickup_enabled,
        'gallery': store.images.all(),
        'updates': store.updates.select_related('product')[:20],
        'is_subscribed': is_subscribed,
    })


# ── Product views ─────────────────────────────────────────────────────────────

def product_detail_view(request, store_pk, product_pk):
    store = get_object_or_404(Store, pk=store_pk, is_active=True)
    product = get_object_or_404(
        Product.objects
               .select_related('store__category', 'store__owner')
               .prefetch_related('images'),
        pk=product_pk,
        store=store,
        is_available=True,
    )
    return render(request, 'delivery/product_detail.html', {
        'store': store,
        'product': product,
        'cart_enabled': settings.DELIVERY_CART_ENABLED,
    })


# ── Cart view ─────────────────────────────────────────────────────────────────

@login_required
def cart_view(request):
    """Foydalanuvchi savati sahifasi."""
    cart, _ = Cart.objects.get_or_create(user=request.user)
    _ = cart.items.select_related('product__store').prefetch_related('product__images')
    return render(request, 'delivery/cart.html', {'cart': cart})


# ── CHECKOUT / BUYURTMA ─────────────────────────────────────────────────────────

@login_required
def checkout(request):
    """Savatni buyurtmaga aylantirish: manzil + demo to'lov.

    Har do'kon o'z rejimida: pickup (olib ketish) do'konlarida yetkazish narxi
    yo'q, manzil talab qilinmaydi va to'lov MAJBURIY oldindan karta orqali
    (naqd RUXSAT ETILMAYDI). Yetkazib berish do'konlari — eski oqim.
    """
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = list(cart.items.select_related('product__store'))

    if not items:
        messages.warning(request, "Savatingiz bo'sh. Avval mahsulot qo'shing.")
        return redirect('delivery:cart')

    # Mavjud bo'lmagan / sotuvdan olingan mahsulotlarni savatdan tozalash
    invalid = [it for it in items if not it.product.is_available]
    if invalid:
        for it in invalid:
            it.delete()
        messages.warning(request, "Ayrim mahsulotlar sotuvda yo'q — savatdan olib tashlandi.")
        return redirect('delivery:cart')

    subtotal = sum(it.product.price * it.quantity for it in items)
    # Har do'kon alohida buyurtma. Pickup do'konlarida yetkazish narxi yo'q.
    store_ids = {it.product.store_id for it in items}
    delivery_store_count = len({it.product.store_id for it in items if not it.product.store.pickup_enabled})
    has_pickup = any(it.product.store.pickup_enabled for it in items)
    has_delivery = any(not it.product.store.pickup_enabled for it in items)
    delivery_fee = DELIVERY_FEE * delivery_store_count
    total = int(subtotal) + delivery_fee

    base_ctx = {
        'cart': cart, 'items': items, 'subtotal': int(subtotal),
        'delivery_fee': delivery_fee, 'total': total, 'store_count': len(store_ids),
        'has_pickup': has_pickup, 'has_delivery': has_delivery,
    }

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        note = request.POST.get('note', '').strip()
        method = request.POST.get('payment_method', 'card')
        try:
            pickup_at = _parse_datetime_local(request.POST.get('pickup_at'))
        except ValueError:
            pickup_at = None

        if not phone:
            messages.error(request, "Telefon majburiy.")
            return render(request, 'delivery/checkout.html', base_ctx)
        # Manzil faqat yetkazib berish buyurtmasi bo'lsa majburiy.
        if has_delivery and not address:
            messages.error(request, "Yetkazib berish uchun manzil majburiy.")
            return render(request, 'delivery/checkout.html', base_ctx)
        # Pickup uchun to'lov MAJBURIY oldindan — naqd ruxsat etilmaydi.
        if has_pickup and method != 'card':
            messages.error(request, "Olib ketish buyurtmasi faqat karta orqali oldindan to'lanadi.")
            return render(request, 'delivery/checkout.html', base_ctx)

        card_last4 = card_brand = ''
        payment_status = 'unpaid'
        if method == 'card':
            digits = ''.join(c for c in request.POST.get('card_number', '') if c.isdigit())
            cvv = request.POST.get('cvv', '').strip()
            expiry = request.POST.get('expiry', '').strip()
            if len(digits) < 16 or len(cvv) < 3 or not expiry:
                messages.error(request, "Karta ma'lumotlari to'liq emas.")
                return render(request, 'delivery/checkout.html', base_ctx)
            # DIQQAT: to'liq karta raqami va CVV SAQLANMAYDI.
            card_last4 = digits[-4:]
            card_brand = _card_brand(digits)
            payment_status = 'paid'

        # Buyurtmalarni do'kon bo'yicha bo'lib yaratish (multi-store split) —
        # stock tranzaksiya ichida lock qilinadi (oversell himoyasi).
        created_orders = []
        with transaction.atomic():
            product_ids = [it.product_id for it in items]
            locked = {p.pk: p for p in
                      Product.objects.select_for_update().filter(pk__in=product_ids)}
            for it in items:
                p = locked.get(it.product_id)
                if p is None or not p.is_available:
                    messages.warning(request, "Ayrim mahsulotlar sotuvda yo'q. Savatni yangilang.")
                    return redirect('delivery:cart')
                if it.quantity > p.stock:
                    messages.error(request, f"'{p.name}' uchun omborda faqat {p.stock} dona qoldi.")
                    return redirect('delivery:cart')

            groups = {}
            for it in items:
                p = locked[it.product_id]
                groups.setdefault(p.store_id, []).append((it, p))

            for store_id, group in groups.items():
                store = group[0][1].store
                is_pickup = store.pickup_enabled
                fee = 0 if is_pickup else DELIVERY_FEE
                g_subtotal = int(sum(p.price * it.quantity for it, p in group))
                # Pickup + oldindan to'langan bo'lsa darhol 'to'landi' (accepted).
                o_status = 'accepted' if (is_pickup and payment_status == 'paid') else 'pending'
                order = Order.objects.create(
                    user=request.user, full_name=full_name or (request.user.name or ''),
                    phone=phone, address=('' if is_pickup else address), note=note,
                    subtotal=g_subtotal, delivery_fee=fee, total=g_subtotal + fee,
                    status=o_status, payment_method=method, payment_status=payment_status,
                    card_last4=card_last4, card_brand=card_brand,
                    fulfillment_type='pickup' if is_pickup else 'delivery',
                    pickup_at=pickup_at if is_pickup else None,
                )
                for it, p in group:
                    OrderItem.objects.create(
                        order=order, product=p, product_name=p.name,
                        store_name=p.store.name, price=p.price, quantity=it.quantity,
                    )
                    p.stock = max(0, p.stock - it.quantity)
                    p.save(update_fields=['stock'])
                created_orders.append(order)

            cart.items.all().delete()

        # Do'kon egalariga yangi buyurtma haqida bildirishnoma (bittadan)
        try:
            from notifications.models import notify
            from django.urls import reverse
            url = reverse('delivery:store_orders')
            notified = set()
            for it in items:
                owner_id = it.product.store.owner_id
                if owner_id != request.user.id and owner_id not in notified:
                    notify(it.product.store.owner, "Yangi buyurtma keldi 🧾", url, 'order')
                    notified.add(owner_id)
        except Exception:
            pass

        n = len(created_orders)
        if n > 1:
            messages.success(request, f"{n} ta do'kondan buyurtma qabul qilindi! ✅")
        elif has_pickup:
            messages.success(request, "To'lov amalga oshirildi! Buyurtma tayyor bo'lganda xabar beramiz. 🛍️")
        elif method == 'card':
            messages.success(request, "To'lov amalga oshirildi va buyurtma qabul qilindi! ✅")
        else:
            messages.success(request, "Buyurtma qabul qilindi! To'lov yetkazishda naqd. ✅")

        # Bitta buyurtma bo'lsa — uning sahifasiga, aks holda buyurtmalar ro'yxatiga.
        if n == 1:
            return redirect('delivery:order_detail', order_id=created_orders[0].id)
        return redirect('delivery:my_orders')

    return render(request, 'delivery/checkout.html', base_ctx)


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related('items'), pk=order_id, user=request.user,
    )
    return render(request, 'delivery/order_detail.html', {'order': order})


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'delivery/my_orders.html', {'orders': orders})


# ── REAL-TIME TRACKING ──────────────────────────────────────────────────────────

@login_required
def order_track(request, order_id):
    """Customer live-tracking page (map + moving driver marker + status)."""
    order = get_object_or_404(
        Order.objects.select_related('driver').prefetch_related('items__product__store'),
        pk=order_id,
    )
    # Auth: only the customer, the assigned driver, or staff.
    is_driver = order.driver and order.driver.user_id == request.user.id
    if order.user_id != request.user.id and not is_driver and not request.user.is_staff:
        messages.error(request, "Bu buyurtmani kuzatish huquqingiz yo'q.")
        return redirect('delivery:my_orders')

    store = None
    first = order.items.first()
    if first and first.product and first.product.store:
        store = first.product.store

    loc = DriverLocation.objects.filter(driver=order.driver).first() if order.driver else None

    return render(request, 'delivery/order_track.html', {
        'order': order,
        'store': store,
        'driver_location': loc,
    })


@login_required
@require_POST
@ratelimit('driver_loc', limit=40, window=60)
def driver_update_location(request):
    """API: driver pushes their current GPS coordinates.

    Stores the latest location and broadcasts it to the tracking rooms of all
    the driver's currently active deliveries.
    """
    driver = _get_driver(request)
    if not driver:
        return JsonResponse({'ok': False, 'error': 'not_a_driver'}, status=403)

    try:
        lat = float(request.POST.get('lat'))
        lng = float(request.POST.get('lng'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'bad_coords'}, status=400)

    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return JsonResponse({'ok': False, 'error': 'out_of_range'}, status=400)

    def _f(key):
        try:
            return float(request.POST.get(key))
        except (TypeError, ValueError):
            return None

    heading, speed = _f('heading'), _f('speed')

    DriverLocation.objects.update_or_create(
        driver=driver,
        defaults={'latitude': lat, 'longitude': lng, 'heading': heading, 'speed': speed},
    )

    # Broadcast to all active deliveries this driver is handling.
    active_ids = list(
        Order.objects.filter(driver=driver, status__in=ACTIVE_DELIVERY_STATUSES)
        .values_list('id', flat=True)
    )
    push_driver_location_for_orders(active_ids, lat, lng, heading, speed)

    return JsonResponse({'ok': True, 'broadcast_to': len(active_ids)})


# ── STORE MANAGEMENT (egasi) ────────────────────────────────────────────────────

def _int_or_none(v):
    try:
        return int(str(v).replace(' ', '').replace(',', ''))
    except (TypeError, ValueError):
        return None


def _pfloat(v):
    """Xaritadan kelgan koordinatani xavfsiz float'ga aylantiradi."""
    try:
        f = float(str(v).strip())
    except (TypeError, ValueError):
        return None
    return f if -180 <= f <= 180 else None


@login_required
def my_stores(request):
    stores = Store.objects.filter(owner=request.user).select_related('category')
    return render(request, 'delivery/my_stores.html', {'stores': stores})


def _form_post(request):
    """Forma qiymatlari: yo'q kalit '' (template crash bo'lmasligi uchun)."""
    from collections import defaultdict
    d = defaultdict(str)
    if request.method == 'POST':
        d.update(request.POST.dict())
    return d


def _save_gallery_images(request, store):
    """`gallery` maydonidagi yangi rasmlarni saqlaydi (StoreImage.MAX_IMAGES chegarasi bilan)."""
    files = request.FILES.getlist('gallery')
    if not files:
        return
    remaining = StoreImage.MAX_IMAGES - store.images.count()
    if remaining <= 0:
        messages.warning(request, f"Galereyada {StoreImage.MAX_IMAGES} tadan ko'p rasm bo'lishi mumkin emas.")
        return
    for f in files[:remaining]:
        try:
            validate_file_type(f)
            StoreImage.objects.create(store=store, image=f)
        except Exception as e:
            messages.warning(request, f"Galereya rasmi: {str(e)}")


@login_required
def store_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, "Do'kon nomi majburiy.")
            return render(request, 'delivery/store_form.html', {
                'mode': 'create', 'categories': DeliveryCategory.objects.all(), 'post': _form_post(request),
            })
        store = Store(
            owner=request.user, name=name,
            description=request.POST.get('description', '').strip(),
            address=request.POST.get('address', '').strip(),
            phone=request.POST.get('phone', '').strip(),
            working_hours=request.POST.get('working_hours', '').strip(),
            owner_bio=request.POST.get('owner_bio', '').strip(),
            pickup_enabled='pickup_enabled' in request.POST,
            latitude=_pfloat(request.POST.get('latitude')),
            longitude=_pfloat(request.POST.get('longitude')),
            is_active='is_active' in request.POST or True,
        )
        cat_id = request.POST.get('category')
        if cat_id:
            store.category = DeliveryCategory.objects.filter(pk=cat_id).first()
        logo = request.FILES.get('logo')
        if logo:
            try:
                validate_file_type(logo)
                store.logo = logo
            except Exception as e:
                messages.error(request, f"Logo: {str(e)}")
        owner_photo = request.FILES.get('owner_photo')
        if owner_photo:
            try:
                validate_file_type(owner_photo)
                store.owner_photo = owner_photo
            except Exception as e:
                messages.error(request, f"Egasi rasmi: {str(e)}")
        store.save()
        _save_gallery_images(request, store)
        # Do'kon ochgan foydalanuvchi avtomatik 'business' roliga o'tadi
        if request.user.role == 'user':
            request.user.role = 'business'
            request.user.save(update_fields=['role'])
        messages.success(request, "Do'kon yaratildi! ✅")
        return redirect('delivery:store_detail', pk=store.pk)

    return render(request, 'delivery/store_form.html', {
        'mode': 'create', 'categories': DeliveryCategory.objects.all(),
        'post': _form_post(request),
    })


@login_required
def store_edit(request, pk):
    store = get_object_or_404(Store, pk=pk)
    if store.owner_id != request.user.id:
        messages.error(request, "Bu do'konni tahrirlash huquqingiz yo'q.")
        return redirect('delivery:store_detail', pk=pk)

    if request.method == 'POST':
        store.name = request.POST.get('name', '').strip() or store.name
        store.description = request.POST.get('description', '').strip()
        store.address = request.POST.get('address', '').strip()
        store.phone = request.POST.get('phone', '').strip()
        store.working_hours = request.POST.get('working_hours', '').strip()
        store.owner_bio = request.POST.get('owner_bio', '').strip()
        store.pickup_enabled = 'pickup_enabled' in request.POST
        _lat = _pfloat(request.POST.get('latitude'))
        _lng = _pfloat(request.POST.get('longitude'))
        if _lat is not None and _lng is not None:
            store.latitude, store.longitude = _lat, _lng
        store.is_active = 'is_active' in request.POST
        cat_id = request.POST.get('category')
        store.category = DeliveryCategory.objects.filter(pk=cat_id).first() if cat_id else None
        logo = request.FILES.get('logo')
        if logo:
            try:
                validate_file_type(logo)
                store.logo = logo
            except Exception as e:
                messages.error(request, f"Logo: {str(e)}")
        owner_photo = request.FILES.get('owner_photo')
        if owner_photo:
            try:
                validate_file_type(owner_photo)
                store.owner_photo = owner_photo
            except Exception as e:
                messages.error(request, f"Egasi rasmi: {str(e)}")
        store.save()
        remove_ids = request.POST.getlist('remove_image')
        if remove_ids:
            StoreImage.objects.filter(store=store, pk__in=remove_ids).delete()
        _save_gallery_images(request, store)
        messages.success(request, "Do'kon yangilandi! ✅")
        return redirect('delivery:store_detail', pk=store.pk)

    return render(request, 'delivery/store_form.html', {
        'mode': 'edit', 'store': store, 'categories': DeliveryCategory.objects.all(),
        'gallery': store.images.all(),
        'post': _form_post(request),
    })


@login_required
def store_delete(request, pk):
    store = get_object_or_404(Store, pk=pk, owner=request.user)
    if request.method == 'POST':
        store.delete()
        messages.success(request, "Do'kon o'chirildi.")
        return redirect('delivery:my_stores')
    return render(request, 'delivery/store_confirm_delete.html', {'store': store})


@login_required
@require_POST
def store_announcement_create(request, pk):
    store = get_object_or_404(Store, pk=pk, owner=request.user)
    text = request.POST.get('text', '').strip()
    if not text:
        messages.error(request, "E'lon matni bo'sh bo'lishi mumkin emas.")
        return redirect('delivery:store_detail', pk=store.pk)
    image = request.FILES.get('image')
    if image:
        try:
            validate_file_type(image)
        except Exception as e:
            messages.warning(request, f"Rasm: {str(e)}")
            image = None
    create_store_update(store, 'announcement', text=text, image=image)
    messages.success(request, "E'lon joylandi! ✅")
    return redirect('delivery:store_detail', pk=store.pk)


@login_required
@require_POST
def store_subscribe_toggle(request, pk):
    """Foydalanuvchi do'kon yangiliklaridan xabardor bo'lish (yoqish/o'chirish)."""
    store = get_object_or_404(Store, pk=pk)
    sub, created = StoreSubscription.objects.get_or_create(
        store=store, user=request.user, defaults={'is_enabled': True})
    if not created:
        sub.is_enabled = not sub.is_enabled
        sub.save(update_fields=['is_enabled'])
    messages.success(
        request,
        "Bildirishnomalar yoqildi 🔔" if sub.is_enabled else "Bildirishnomalar o'chirildi",
    )
    return redirect('delivery:store_detail', pk=store.pk)


# ── DO'KON BILAN CHAT (mijoz ↔ do'kon) ──────────────────────────────────────────

@login_required
def store_chat_start(request, store_pk):
    """Mijoz do'kon bilan chatni boshlaydi (yoki mavjudini ochadi)."""
    store = get_object_or_404(Store, pk=store_pk, is_active=True)
    if store.owner_id == request.user.id:
        # Egasi o'z do'koni bilan chat qilmaydi — kelgan xabarlar panelga o'tsin.
        return redirect('delivery:store_chat_inbox')
    thread = get_or_create_thread(store, request.user)
    return redirect('delivery:store_chat_thread', thread_id=thread.id)


@login_required
def store_chat_thread(request, thread_id):
    """Chat oynasi — xabarlar tarixi + yozish maydoni (real-time WS bilan)."""
    thread = get_object_or_404(
        StoreChatThread.objects.select_related('store', 'customer'), pk=thread_id)
    if not is_participant(thread, request.user):
        messages.error(request, "Bu suhbatga kirish huquqingiz yo'q.")
        return redirect('delivery:store_list')

    # Qarshi tomon xabarlarini o'qilgan deb belgilaymiz.
    thread.messages.exclude(sender=request.user).filter(is_read=False).update(is_read=True)

    is_owner = request.user.id == thread.store.owner_id
    return render(request, 'delivery/store_chat_thread.html', {
        'thread': thread,
        'store': thread.store,
        'messages_list': thread.messages.all(),
        'is_owner': is_owner,
    })


@login_required
@require_POST
def store_chat_send(request, thread_id):
    """Xabar yuborish (JS o'chirilgan holat uchun fallback — WS bo'lmasa)."""
    thread = get_object_or_404(StoreChatThread.objects.select_related('store'), pk=thread_id)
    if not is_participant(thread, request.user):
        messages.error(request, "Bu suhbatga yozish huquqingiz yo'q.")
        return redirect('delivery:store_list')
    text = request.POST.get('text', '').strip()
    if text:
        create_message(thread, request.user, text)
    return redirect('delivery:store_chat_thread', thread_id=thread.id)


@login_required
def store_chat_inbox(request):
    """Do'kon egasi paneli — do'konlariga kelgan barcha suhbatlar (eng so'nggisi tepada)."""
    threads = (
        StoreChatThread.objects
        .filter(store__owner=request.user)
        .select_related('store', 'customer')
        .order_by('-updated_at')
    )
    return render(request, 'delivery/store_chat_inbox.html', {'threads': threads})


# ── PRODUCT MANAGEMENT (egasi) ──────────────────────────────────────────────────

def _parse_datetime_local(v):
    """<input type=datetime-local> qiymatini timezone-aware datetime'ga aylantiradi."""
    if not v:
        return None
    parsed = timezone.datetime.fromisoformat(v)
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed


@login_required
def product_create(request, store_pk):
    store = get_object_or_404(Store, pk=store_pk, owner=request.user)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        price = _int_or_none(request.POST.get('price'))
        if not name or price is None:
            messages.error(request, "Mahsulot nomi va narxi majburiy.")
            return render(request, 'delivery/product_form.html', {'mode': 'create', 'store': store, 'post': _form_post(request)})
        is_available = 'is_available' in request.POST
        stock = _int_or_none(request.POST.get('stock')) or 0
        # restock_at faqat mahsulot tugagan (stock==0) bo'lsa ma'noli.
        try:
            restock_at = _parse_datetime_local(request.POST.get('restock_at')) if stock <= 0 else None
        except ValueError:
            restock_at = None
        product = Product.objects.create(
            store=store, name=name,
            description=request.POST.get('description', '').strip(),
            price=price, stock=stock,
            is_available=is_available, restock_at=restock_at,
        )
        img = request.FILES.get('image')
        if img:
            try:
                validate_file_type(img)
                ProductImage.objects.create(product=product, image=img)
            except Exception as e:
                messages.warning(request, f"Rasm: {str(e)}")
        create_store_update(store, 'new_product', product=product,
                            text=f"Yangi mahsulot: {product.name}")
        messages.success(request, "Mahsulot qo'shildi! ✅")
        return redirect('delivery:store_detail', pk=store.pk)
    return render(request, 'delivery/product_form.html', {'mode': 'create', 'store': store, 'post': _form_post(request)})


@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product.objects.select_related('store'), pk=pk)
    if product.store.owner_id != request.user.id:
        messages.error(request, "Bu mahsulotni tahrirlash huquqingiz yo'q.")
        return redirect('delivery:store_detail', pk=product.store.pk)

    if request.method == 'POST':
        old_price = product.price
        was_in_stock = product.stock > 0

        product.name = request.POST.get('name', '').strip() or product.name
        product.description = request.POST.get('description', '').strip()
        price = _int_or_none(request.POST.get('price'))
        if price is not None:
            product.price = price
        product.stock = _int_or_none(request.POST.get('stock')) or 0
        product.is_available = 'is_available' in request.POST
        # restock_at faqat mahsulot tugagan (stock==0) bo'lsa saqlanadi.
        try:
            product.restock_at = _parse_datetime_local(request.POST.get('restock_at')) if product.stock <= 0 else None
        except ValueError:
            product.restock_at = None
        product.save()
        img = request.FILES.get('image')
        if img:
            try:
                validate_file_type(img)
                ProductImage.objects.create(product=product, image=img)
            except Exception as e:
                messages.warning(request, f"Rasm: {str(e)}")

        if price is not None and price != old_price:
            create_store_update(product.store, 'price_changed', product=product,
                                old_price=old_price, new_price=product.price,
                                text=f"Narx yangilandi: {product.name}")
        now_in_stock = product.stock > 0
        if now_in_stock and not was_in_stock:
            create_store_update(product.store, 'restocked', product=product,
                                text=f"Qayta sotuvga qaytdi: {product.name}")
        elif was_in_stock and not now_in_stock:
            create_store_update(product.store, 'out_of_stock', product=product,
                                text=f"Tugadi: {product.name}")

        messages.success(request, "Mahsulot yangilandi! ✅")
        return redirect('delivery:store_detail', pk=product.store.pk)

    return render(request, 'delivery/product_form.html', {'mode': 'edit', 'product': product, 'store': product.store, 'post': _form_post(request)})


@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product.objects.select_related('store'), pk=pk, store__owner=request.user)
    store_pk = product.store.pk
    if request.method == 'POST':
        product.delete()
        messages.success(request, "Mahsulot o'chirildi.")
        return redirect('delivery:store_detail', pk=store_pk)
    return render(request, 'delivery/product_confirm_delete.html', {'product': product})


# ── STORE ORDER DASHBOARD (egasi) ───────────────────────────────────────────────

ORDER_STATUS_FLOW = ['pending', 'accepted', 'preparing', 'ready', 'delivered']


@login_required
def store_orders(request):
    """Egasiga tegishli do'konlardagi mahsulotlar bo'lgan buyurtmalar."""
    orders = (
        Order.objects.filter(items__product__store__owner=request.user)
        .distinct().prefetch_related('items').order_by('-created_at')
    )
    return render(request, 'delivery/store_orders.html', {
        'orders': orders, 'status_flow': ['accepted', 'preparing', 'ready'],
    })


@login_required
def store_order_status(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    # Ruxsat: buyurtmada egasining do'konidan mahsulot bo'lishi shart
    owns = order.items.filter(product__store__owner=request.user).exists()
    if not owns:
        messages.error(request, "Bu buyurtmani boshqarish huquqingiz yo'q.")
        return redirect('delivery:store_orders')
    if request.method == 'POST':
        new_status = request.POST.get('status', '')
        owner_allowed = {'accepted', 'preparing', 'ready', 'cancelled'}
        # Pickup buyurtmasini to'lanmagan holda "yig'ishni" boshlab bo'lmaydi —
        # to'lov MAJBURIY oldindan (naqd yo'q, karta orqali to'langan bo'lishi shart).
        if order.is_pickup and not order.is_paid and new_status in {'preparing', 'ready'}:
            messages.error(request, "Bu buyurtma hali to'lanmagan.")
        elif new_status not in owner_allowed:
            messages.error(request, "Bu holatni faqat haydovchi o'zgartiradi.")
        elif not can_transition(order.status, new_status, order.fulfillment_type):
            messages.error(request, f"«{order.progress_label()}» dan bu holatga o'tib bo'lmaydi.")
        else:
            order.status = new_status
            update_fields = ['status']
            # Pickup: "tayyor" bo'lganda vaqtni belgilaymiz va mijozga xabar beramiz.
            if order.is_pickup and new_status == 'ready':
                order.ready_for_pickup_at = timezone.now()
                update_fields.append('ready_for_pickup_at')
            order.save(update_fields=update_fields)
            push_order_status(order)   # jonli yangilash (mijoz/haydovchi)
            if order.is_pickup and new_status == 'ready':
                _notify_customer_pickup_ready(order)
            messages.success(request, "Buyurtma holati yangilandi.")
    return redirect('delivery:store_orders')


def _notify_customer_pickup_ready(order):
    """Pickup buyurtma tayyor bo'lganda mijozga bildirishnoma (best-effort)."""
    try:
        from notifications.models import notify
        from django.urls import reverse
        url = reverse('delivery:order_detail', args=[order.id])
        notify(order.user, "Buyurtmangiz tayyor, olib keting! 🛍️", url, 'order')
    except Exception:
        pass


@login_required
@require_POST
def order_confirm_pickup(request, order_id):
    """Mijoz buyurtmani qo'lga olganini tasdiqlaydi — SHUNDAGINA yakunlanadi.

    Faqat buyurtma egasi (mijoz) chaqira oladi va faqat pickup + 'ready' holatida.
    """
    order = get_object_or_404(Order, pk=order_id)
    if order.user_id != request.user.id:
        messages.error(request, "Bu buyurtmani tasdiqlash huquqingiz yo'q.")
        return redirect('delivery:my_orders')
    if not order.can_customer_confirm_pickup:
        messages.error(request, "Buyurtma hali tayyor emas yoki olib ketish buyurtmasi emas.")
        return redirect('delivery:order_detail', order_id=order.id)
    order.status = 'delivered'
    order.customer_confirmed_at = timezone.now()
    order.save(update_fields=['status', 'customer_confirmed_at'])
    push_order_status(order)
    messages.success(request, "Buyurtmani qabul qilganingiz tasdiqlandi. Rahmat! ✅")
    return redirect('delivery:order_detail', order_id=order.id)


# ── DELIVERY DRIVER ─────────────────────────────────────────────────────────────

import logging

logger = logging.getLogger(__name__)


def _get_driver(request):
    return DeliveryDriver.objects.filter(user=request.user).first()


def _normalize_phone(phone):
    """Telefon raqamini +998... formatiga keltiradi."""
    digits = ''.join(c for c in str(phone or '') if c.isdigit())
    if not digits:
        return ''
    if digits.startswith('998'):
        return '+' + digits
    if len(digits) == 9:
        return '+998' + digits
    return '+' + digits if phone and str(phone).startswith('+') else digits


@login_required
def driver_register(request):
    if _get_driver(request):
        return redirect('delivery:driver_dashboard')
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone = _normalize_phone(request.POST.get('phone', '').strip())
        if not full_name or not phone:
            messages.error(request, "Ism va telefon majburiy.")
            return render(request, 'delivery/driver_register.html', {'mode': 'register', 'vehicles': DeliveryDriver.VEHICLE_CHOICES})
        try:
            with transaction.atomic():
                DeliveryDriver.objects.create(
                    user=request.user, full_name=full_name, phone=phone,
                    vehicle_type=request.POST.get('vehicle_type', 'moto'),
                    vehicle_number=request.POST.get('vehicle_number', '').strip(),
                )
                if request.user.role == 'user':
                    request.user.role = 'driver'
                    request.user.save(update_fields=['role'])
        except Exception:
            logger.exception('driver_register failed for user %s', request.user.pk)
            messages.error(request, "Haydovchi profili yaratishda xatolik. Qayta urinib ko'ring.")
            return render(request, 'delivery/driver_register.html', {'mode': 'register', 'vehicles': DeliveryDriver.VEHICLE_CHOICES})
        messages.success(request, "Haydovchi profili yaratildi! ✅")
        return redirect('delivery:driver_dashboard')
    return render(request, 'delivery/driver_register.html', {'mode': 'register', 'vehicles': DeliveryDriver.VEHICLE_CHOICES})


@login_required
def driver_profile(request):
    driver = _get_driver(request)
    if not driver:
        return redirect('delivery:driver_register')
    if request.method == 'POST':
        driver.full_name = request.POST.get('full_name', '').strip() or driver.full_name
        driver.phone = request.POST.get('phone', '').strip() or driver.phone
        driver.vehicle_type = request.POST.get('vehicle_type', driver.vehicle_type)
        driver.vehicle_number = request.POST.get('vehicle_number', '').strip()
        driver.save()
        messages.success(request, "Profil yangilandi. ✅")
        return redirect('delivery:driver_dashboard')
    return render(request, 'delivery/driver_register.html', {'mode': 'edit', 'driver': driver, 'vehicles': DeliveryDriver.VEHICLE_CHOICES})


@login_required
def driver_toggle_available(request):
    driver = _get_driver(request)
    if driver and request.method == 'POST':
        driver.is_available = not driver.is_available
        driver.save(update_fields=['is_available'])
        messages.success(request, "Holat yangilandi: " + ("Bo'sh ✅" if driver.is_available else "Band ⛔"))
    return redirect('delivery:driver_dashboard')


@login_required
def driver_dashboard(request):
    driver = _get_driver(request)
    if not driver:
        return redirect('delivery:driver_register')
    base = Order.objects.select_related('driver').prefetch_related('items')
    # Pickup buyurtmalari haydovchini talab qilmaydi (mijoz o'zi olib ketadi) —
    # 'ready' bo'lsa ham haydovchi ro'yxatida ko'rinmasligi kerak.
    available = base.filter(status='ready', driver__isnull=True, fulfillment_type='delivery')
    my_active = base.filter(driver=driver, status__in=['assigned', 'on_the_way'])
    history = base.filter(driver=driver, status='delivered')
    earnings = history.aggregate(s=Sum('delivery_fee'))['s'] or 0
    return render(request, 'delivery/driver_dashboard.html', {
        'driver': driver, 'available': available, 'my_active': my_active,
        'history': history[:20], 'earnings': earnings, 'delivered_count': history.count(),
    })


@login_required
def order_accept(request, order_id):
    driver = _get_driver(request)
    if not driver:
        return redirect('delivery:driver_register')
    if request.method == 'POST':
        if not driver.is_available:
            messages.error(request, "Avval «Bo'sh» holatiga o'ting.")
            return redirect('delivery:driver_dashboard')
        # Race-himoya: qatorni qulflaymiz — ikki haydovchi bir buyurtmani
        # bir vaqtda ola olmaydi. Ikkinchisi qulf ochilgach bo'sh emasligini ko'radi.
        taken = False
        with transaction.atomic():
            order = (Order.objects.select_for_update()
                     .filter(pk=order_id, status='ready', driver__isnull=True,
                             fulfillment_type='delivery').first())
            if order is not None:
                order.driver = driver
                order.status = 'assigned'
                order.assigned_at = timezone.now()
                order.save(update_fields=['driver', 'status', 'assigned_at'])
                taken = True
        if taken:
            push_order_status(order)
            messages.success(request, "Buyurtma qabul qilindi! 🚗")
        else:
            messages.error(request, "Buyurtma allaqachon olingan yoki mavjud emas.")
    return redirect('delivery:driver_dashboard')


@login_required
def order_release(request, order_id):
    driver = _get_driver(request)
    if request.method == 'POST' and driver:
        order = get_object_or_404(Order, pk=order_id, driver=driver, status='assigned')
        order.driver = None
        order.status = 'ready'
        order.assigned_at = None
        order.save(update_fields=['driver', 'status', 'assigned_at'])
        push_order_status(order)
        messages.success(request, "Buyurtmadan voz kechildi.")
    return redirect('delivery:driver_dashboard')


@login_required
def driver_order_status(request, order_id):
    driver = _get_driver(request)
    if request.method == 'POST' and driver:
        order = get_object_or_404(Order, pk=order_id, driver=driver)
        new_status = request.POST.get('status', '')
        if new_status in {'picked_up', 'on_the_way', 'delivered'} and can_transition(order.status, new_status):
            order.status = new_status
            order.save(update_fields=['status'])
            push_order_status(order)
            messages.success(request, "Holat yangilandi.")
        else:
            messages.error(request, "Noto'g'ri o'tish.")
    return redirect('delivery:driver_dashboard')
