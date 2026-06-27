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
    DeliveryCategory, Store, Product, ProductImage, Cart, Order, OrderItem,
    DeliveryDriver, DriverLocation, can_transition,
)
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

    return render(request, 'delivery/store_detail.html', {
        'store': store,
        'products': products_qs,
        'pq': pq,
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
    """Savatni buyurtmaga aylantirish: manzil + demo to'lov."""
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
    # Har do'kon alohida buyurtma → har biri uchun yetkazish narxi alohida.
    store_count = len({it.product.store_id for it in items})
    delivery_fee = DELIVERY_FEE * store_count
    total = int(subtotal) + delivery_fee

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        note = request.POST.get('note', '').strip()
        method = request.POST.get('payment_method', 'card')

        ctx = {
            'cart': cart, 'items': items, 'subtotal': int(subtotal),
            'delivery_fee': delivery_fee, 'total': total, 'store_count': store_count,
        }

        if not phone or not address:
            messages.error(request, "Telefon va manzil majburiy.")
            return render(request, 'delivery/checkout.html', ctx)

        card_last4 = card_brand = ''
        payment_status = 'unpaid'
        if method == 'card':
            digits = ''.join(c for c in request.POST.get('card_number', '') if c.isdigit())
            cvv = request.POST.get('cvv', '').strip()
            expiry = request.POST.get('expiry', '').strip()
            if len(digits) < 16 or len(cvv) < 3 or not expiry:
                messages.error(request, "Karta ma'lumotlari to'liq emas.")
                return render(request, 'delivery/checkout.html', ctx)
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
                g_subtotal = int(sum(p.price * it.quantity for it, p in group))
                order = Order.objects.create(
                    user=request.user, full_name=full_name or (request.user.name or ''),
                    phone=phone, address=address, note=note,
                    subtotal=g_subtotal, delivery_fee=DELIVERY_FEE, total=g_subtotal + DELIVERY_FEE,
                    status='pending', payment_method=method, payment_status=payment_status,
                    card_last4=card_last4, card_brand=card_brand,
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
        elif method == 'card':
            messages.success(request, "To'lov amalga oshirildi va buyurtma qabul qilindi! ✅")
        else:
            messages.success(request, "Buyurtma qabul qilindi! To'lov yetkazishda naqd. ✅")

        # Bitta buyurtma bo'lsa — uning sahifasiga, aks holda buyurtmalar ro'yxatiga.
        if n == 1:
            return redirect('delivery:order_detail', order_id=created_orders[0].id)
        return redirect('delivery:my_orders')

    return render(request, 'delivery/checkout.html', {
        'cart': cart, 'items': items, 'subtotal': int(subtotal),
        'delivery_fee': delivery_fee, 'total': total, 'store_count': store_count,
    })


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
        store.save()
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
        store.save()
        messages.success(request, "Do'kon yangilandi! ✅")
        return redirect('delivery:store_detail', pk=store.pk)

    return render(request, 'delivery/store_form.html', {
        'mode': 'edit', 'store': store, 'categories': DeliveryCategory.objects.all(),
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


# ── PRODUCT MANAGEMENT (egasi) ──────────────────────────────────────────────────

@login_required
def product_create(request, store_pk):
    store = get_object_or_404(Store, pk=store_pk, owner=request.user)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        price = _int_or_none(request.POST.get('price'))
        if not name or price is None:
            messages.error(request, "Mahsulot nomi va narxi majburiy.")
            return render(request, 'delivery/product_form.html', {'mode': 'create', 'store': store, 'post': _form_post(request)})
        product = Product.objects.create(
            store=store, name=name,
            description=request.POST.get('description', '').strip(),
            price=price, stock=_int_or_none(request.POST.get('stock')) or 0,
            is_available='is_available' in request.POST,
        )
        img = request.FILES.get('image')
        if img:
            try:
                validate_file_type(img)
                ProductImage.objects.create(product=product, image=img)
            except Exception as e:
                messages.warning(request, f"Rasm: {str(e)}")
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
        product.name = request.POST.get('name', '').strip() or product.name
        product.description = request.POST.get('description', '').strip()
        price = _int_or_none(request.POST.get('price'))
        if price is not None:
            product.price = price
        product.stock = _int_or_none(request.POST.get('stock')) or 0
        product.is_available = 'is_available' in request.POST
        product.save()
        img = request.FILES.get('image')
        if img:
            try:
                validate_file_type(img)
                ProductImage.objects.create(product=product, image=img)
            except Exception as e:
                messages.warning(request, f"Rasm: {str(e)}")
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
        if new_status not in owner_allowed:
            messages.error(request, "Bu holatni faqat haydovchi o'zgartiradi.")
        elif not can_transition(order.status, new_status):
            messages.error(request, f"«{order.get_status_display()}» dan bu holatga o'tib bo'lmaydi.")
        else:
            order.status = new_status
            order.save(update_fields=['status'])
            push_order_status(order)   # jonli yangilash (mijoz/haydovchi)
            messages.success(request, "Buyurtma holati yangilandi.")
    return redirect('delivery:store_orders')


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
    available = base.filter(status='ready', driver__isnull=True)
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
                     .filter(pk=order_id, status='ready', driver__isnull=True).first())
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
