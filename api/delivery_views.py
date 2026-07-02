"""Delivery (yetkazish) API view'lari: do'konlar, mahsulotlar, savat, buyurtma."""
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import generics, viewsets, status
from rest_framework.decorators import (
    api_view, permission_classes as perm, throttle_classes,
)
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from delivery.models import (
    Store, StoreImage, Product, Cart, CartItem, Order, OrderItem, DeliveryCategory,
    StoreUpdate, StoreSubscription,
)
from delivery.feed import create_store_update
from .throttles import CheckoutThrottle
from .delivery_serializers import (
    StoreListSerializer, StoreDetailSerializer, ProductSerializer,
    CartSerializer, OrderSerializer, CheckoutSerializer, StoreUpdateSerializer,
)


def _parse_restock_at(raw):
    """Mobil klientdan ISO 8601 vaqt satrini xavfsiz DateTime'ga aylantiradi."""
    if not raw:
        return None
    dt = parse_datetime(str(raw))
    if dt is None:
        return None
    return timezone.make_aware(dt) if timezone.is_naive(dt) else dt

DELIVERY_FEE = 10000  # web bilan bir xil


def _card_brand(digits: str) -> str:
    if digits.startswith('8600'):
        return 'UZCARD'
    if digits.startswith('9860'):
        return 'HUMO'
    if digits.startswith('4'):
        return 'VISA'
    if digits.startswith('5'):
        return 'MASTERCARD'
    return ''


# ── Do'konlar / mahsulotlar ──────────────────────────────────────────────────
class StoreViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    search_fields = ['name', 'description', 'address']
    filterset_fields = ['category']

    def get_queryset(self):
        return Store.objects.filter(is_active=True).select_related('category')

    def get_serializer_class(self):
        return StoreDetailSerializer if self.action == 'retrieve' else StoreListSerializer


class ProductDetailView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, pk):
        try:
            product = Product.objects.prefetch_related('images').get(pk=pk, is_available=True)
        except Product.DoesNotExist:
            return Response({'detail': 'Mahsulot topilmadi.'}, status=404)
        return Response(ProductSerializer(product, context={'request': request}).data)


# ── Savat ─────────────────────────────────────────────────────────────────────
def _cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = _cart(request.user)
        return Response(CartSerializer(cart, context={'request': request}).data)


@api_view(['POST'])
@perm([IsAuthenticated])
def cart_add(request):
    """{product_id, quantity?} — qo'shadi yoki miqdorni oshiradi."""
    product = _get_product(request)
    if product is None:
        return Response({'detail': 'Mahsulot topilmadi.'}, status=404)
    qty = max(1, int(request.data.get('quantity', 1)))
    cart = _cart(request.user)
    item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, defaults={'quantity': 0})
    new_qty = (0 if created else item.quantity) + qty
    if new_qty > product.stock:
        return Response(
            {'detail': f"Omborda faqat {product.stock} dona mavjud."},
            status=status.HTTP_409_CONFLICT)
    item.quantity = new_qty
    item.save()
    return Response(CartSerializer(cart, context={'request': request}).data,
                    status=status.HTTP_201_CREATED)


@api_view(['POST'])
@perm([IsAuthenticated])
def cart_set(request):
    """{product_id, quantity} — miqdorni aniq o'rnatadi (0 = o'chiradi)."""
    product = _get_product(request)
    if product is None:
        return Response({'detail': 'Mahsulot topilmadi.'}, status=404)
    qty = int(request.data.get('quantity', 1))
    cart = _cart(request.user)
    if qty <= 0:
        CartItem.objects.filter(cart=cart, product=product).delete()
    else:
        if qty > product.stock:
            return Response(
                {'detail': f"Omborda faqat {product.stock} dona mavjud."},
                status=status.HTTP_409_CONFLICT)
        CartItem.objects.update_or_create(
            cart=cart, product=product, defaults={'quantity': qty})
    return Response(CartSerializer(cart, context={'request': request}).data)


@api_view(['POST'])
@perm([IsAuthenticated])
def cart_remove(request):
    """{product_id} — savatdan butunlay olib tashlaydi."""
    cart = _cart(request.user)
    CartItem.objects.filter(cart=cart, product_id=request.data.get('product_id')).delete()
    return Response(CartSerializer(cart, context={'request': request}).data)


@api_view(['POST'])
@perm([IsAuthenticated])
def cart_clear(request):
    _cart(request.user).items.all().delete()
    return Response({'detail': 'Savat tozalandi.'})


def _get_product(request):
    return Product.objects.filter(
        pk=request.data.get('product_id'), is_available=True).first()


# ── Buyurtma (checkout + tarix) ───────────────────────────────────────────────
class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return (Order.objects.filter(user=self.request.user)
                .prefetch_related('items').order_by('-created_at'))

    def create(self, request, *args, **kwargs):
        return checkout(request)


@api_view(['POST'])
@perm([IsAuthenticated])
@throttle_classes([CheckoutThrottle])
def checkout(request):
    """Savatni buyurtmaga aylantiradi (web checkout logikasi bilan bir xil)."""
    ser = CheckoutSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    cart = _cart(request.user)
    items = list(cart.items.select_related('product__store'))
    if not items:
        return Response({'detail': "Savatingiz bo'sh."}, status=status.HTTP_400_BAD_REQUEST)

    invalid = [it for it in items if not it.product.is_available]
    if invalid:
        for it in invalid:
            it.delete()
        return Response(
            {'detail': "Ayrim mahsulotlar sotuvda yo'q — savatdan olib tashlandi."},
            status=status.HTTP_409_CONFLICT)

    method = data.get('payment_method', 'card')
    has_pickup = any(it.product.store.pickup_enabled for it in items)
    has_delivery = any(not it.product.store.pickup_enabled for it in items)
    # Pickup uchun to'lov MAJBURIY oldindan (karta/Payme/Click) — naqd RUXSAT
    # ETILMAYDI. Manzil pickup buyurtmasida talab qilinmaydi.
    if has_pickup and method != 'card':
        return Response({'detail': "Olib ketish buyurtmasi faqat karta orqali oldindan to'lanadi."},
                        status=status.HTTP_400_BAD_REQUEST)
    if has_delivery and not (data.get('address') or '').strip():
        return Response({'detail': "Yetkazib berish uchun manzil majburiy."},
                        status=status.HTTP_400_BAD_REQUEST)
    # 'card' — onlayn (Payme/Click) orqali, buyurtma yaratilgach
    # `/api/payments/initiate/` bilan to'lanadi. Buyurtma 'unpaid' yaratiladi;
    # to'langach pickup buyurtmalari avtomatik 'accepted' bo'ladi (gateways).
    payment_status = 'unpaid'
    card_last4 = card_brand = ''
    pickup_at = data.get('pickup_at')

    created_orders = []
    with transaction.atomic():
        # Stockni tranzaksiya ichida qayta tekshiramiz (oversell himoyasi).
        # select_for_update — bir vaqtda kelgan buyurtmalarni ketma-ket bajaradi.
        product_ids = [it.product_id for it in items]
        locked = {p.pk: p for p in
                  Product.objects.select_for_update().filter(pk__in=product_ids)}
        for it in items:
            p = locked.get(it.product_id)
            if p is None or not p.is_available:
                return Response(
                    {'detail': "Ayrim mahsulotlar sotuvda yo'q. Savatni yangilang."},
                    status=status.HTTP_409_CONFLICT)
            if it.quantity > p.stock:
                return Response(
                    {'detail': f"'{p.name}' uchun omborda faqat {p.stock} dona qoldi."},
                    status=status.HTTP_409_CONFLICT)

        # Savatni do'kon bo'yicha guruhlaymiz — har do'kon alohida buyurtma oladi
        # (multi-store split). Pickup do'konlarida yetkazish narxi yo'q.
        groups = {}
        for it in items:
            p = locked[it.product_id]
            groups.setdefault(p.store_id, []).append((it, p))

        for store_id, group in groups.items():
            store = group[0][1].store
            is_pickup = store.pickup_enabled
            fee = 0 if is_pickup else DELIVERY_FEE
            g_subtotal = int(sum(p.price * it.quantity for it, p in group))
            order = Order.objects.create(
                user=request.user,
                full_name=data.get('full_name') or (request.user.name or ''),
                phone=data['phone'],
                address='' if is_pickup else (data.get('address') or ''),
                note=data.get('note', ''),
                subtotal=g_subtotal, delivery_fee=fee, total=g_subtotal + fee,
                status='pending', payment_method=method, payment_status=payment_status,
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

    # Har bir do'kon egasiga bittadan bildirishnoma
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

    ser_out = OrderSerializer(created_orders, many=True, context={'request': request})
    return Response({'orders': ser_out.data, 'count': len(created_orders)},
                    status=status.HTTP_201_CREATED)


# ── EGASI: do'kon va mahsulot boshqaruvi (mobil biznes paneli) ────────────────
class MyStoresView(APIView):
    """GET — egasi do'konlari + kategoriyalar; POST — yangi do'kon."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stores = Store.objects.filter(owner=request.user).select_related('category')
        cats = DeliveryCategory.objects.all()
        return Response({
            'categories': [{'id': c.id, 'name': c.name} for c in cats],
            'results': StoreListSerializer(stores, many=True, context={'request': request}).data,
        })

    def post(self, request):
        name = (request.data.get('name') or '').strip()
        if not name:
            return Response({'detail': "Do'kon nomi majburiy."},
                            status=status.HTTP_400_BAD_REQUEST)
        cat = DeliveryCategory.objects.filter(pk=request.data.get('category')).first() \
            if request.data.get('category') else None
        store = Store.objects.create(
            owner=request.user, name=name,
            description=(request.data.get('description') or '').strip(),
            address=(request.data.get('address') or '').strip(),
            phone=(request.data.get('phone') or '').strip(),
            working_hours=(request.data.get('working_hours') or '').strip(),
            owner_bio=(request.data.get('owner_bio') or '').strip(),
            category=cat, is_active=True,
        )
        if request.FILES.get('logo'):
            store.logo = request.FILES['logo']
        if request.FILES.get('owner_photo'):
            store.owner_photo = request.FILES['owner_photo']
        store.save()
        for f in request.FILES.getlist('gallery')[:StoreImage.MAX_IMAGES]:
            StoreImage.objects.create(store=store, image=f)
        return Response(StoreDetailSerializer(store, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)


class MyStoreDetailView(APIView):
    """PATCH — egasi o'z do'konini tahriylaydi (galereya qo'shish/olib tashlash bilan)."""
    permission_classes = [IsAuthenticated]

    def _get_store(self, request, store_pk):
        return Store.objects.filter(pk=store_pk, owner=request.user).first()

    def patch(self, request, store_pk):
        store = self._get_store(request, store_pk)
        if store is None:
            return Response({'detail': "Do'kon topilmadi yoki ruxsat yo'q."},
                            status=status.HTTP_404_NOT_FOUND)
        for field in ('name', 'description', 'address', 'phone', 'working_hours', 'owner_bio'):
            if field in request.data:
                setattr(store, field, (request.data.get(field) or '').strip())
        if 'category' in request.data:
            cat_id = request.data.get('category')
            store.category = DeliveryCategory.objects.filter(pk=cat_id).first() if cat_id else None
        if 'is_active' in request.data:
            store.is_active = str(request.data.get('is_active')).lower() in ('1', 'true', 'yes')
        if request.FILES.get('logo'):
            store.logo = request.FILES['logo']
        if request.FILES.get('owner_photo'):
            store.owner_photo = request.FILES['owner_photo']
        store.save()

        remove_ids = request.data.getlist('remove_image') if hasattr(request.data, 'getlist') else []
        if remove_ids:
            StoreImage.objects.filter(store=store, pk__in=remove_ids).delete()
        remaining = StoreImage.MAX_IMAGES - store.images.count()
        for f in request.FILES.getlist('gallery')[:max(remaining, 0)]:
            StoreImage.objects.create(store=store, image=f)

        return Response(StoreDetailSerializer(store, context={'request': request}).data)


class StoreProductsView(APIView):
    """POST — egasi o'z do'koniga mahsulot qo'shadi."""
    permission_classes = [IsAuthenticated]

    def post(self, request, store_pk):
        store = Store.objects.filter(pk=store_pk, owner=request.user).first()
        if store is None:
            return Response({'detail': "Do'kon topilmadi yoki ruxsat yo'q."},
                            status=status.HTTP_404_NOT_FOUND)
        name = (request.data.get('name') or '').strip()
        try:
            price = int(str(request.data.get('price') or 0).replace(' ', ''))
        except (ValueError, TypeError):
            price = 0
        if not name or price <= 0:
            return Response({'detail': "Nom va narx to'g'ri kiritilishi shart."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            stock = int(request.data.get('stock') or 0)
        except (ValueError, TypeError):
            stock = 0
        is_available = str(request.data.get('is_available', 'true')).lower() not in ('0', 'false', 'no')
        stock = max(stock, 0)
        product = Product.objects.create(
            store=store, name=name, price=price, stock=stock,
            description=(request.data.get('description') or '').strip(),
            is_available=is_available,
            # restock_at faqat mahsulot tugagan (stock==0) bo'lsa ma'noli.
            restock_at=_parse_restock_at(request.data.get('restock_at')) if stock <= 0 else None,
        )
        create_store_update(store, 'new_product', product=product,
                            text=f"Yangi mahsulot: {product.name}")
        return Response(ProductSerializer(product, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)


class StoreProductDetailView(APIView):
    """PATCH — egasi o'z mahsulotini tahrirlaydi (narx/mavjudlik o'zgarsa —
    StoreUpdate yangiligi va obunachilarga bildirishnoma avtomatik yuboriladi)."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, store_pk, product_pk):
        product = Product.objects.filter(
            pk=product_pk, store_id=store_pk, store__owner=request.user).select_related('store').first()
        if product is None:
            return Response({'detail': "Mahsulot topilmadi yoki ruxsat yo'q."},
                            status=status.HTTP_404_NOT_FOUND)

        old_price = product.price
        was_in_stock = product.stock > 0

        if 'name' in request.data:
            product.name = (request.data.get('name') or product.name).strip() or product.name
        if 'description' in request.data:
            product.description = (request.data.get('description') or '').strip()
        if 'price' in request.data:
            try:
                product.price = int(str(request.data.get('price')).replace(' ', ''))
            except (ValueError, TypeError):
                pass
        if 'stock' in request.data:
            try:
                product.stock = max(0, int(request.data.get('stock')))
            except (ValueError, TypeError):
                pass
        if 'is_available' in request.data:
            product.is_available = str(request.data.get('is_available')).lower() not in ('0', 'false', 'no')
        # restock_at faqat mahsulot tugagan (stock==0) bo'lsa saqlanadi.
        product.restock_at = _parse_restock_at(request.data.get('restock_at')) if product.stock <= 0 else None
        product.save()

        if product.price != old_price:
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

        return Response(ProductSerializer(product, context={'request': request}).data)


# ── Do'kon yangiliklari / obuna (2-qism: bildirishnomalar) ─────────────────────
class StoreUpdatesView(generics.ListAPIView):
    """GET — do'konning 'yangiliklar tasmasi' (sahifalangan, eng yangisi oldin)."""
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = StoreUpdateSerializer

    def get_queryset(self):
        return StoreUpdate.objects.filter(
            store_id=self.kwargs['store_pk']).select_related('product')


class StoreSubscribeToggleView(APIView):
    """POST — do'kon yangiliklaridan xabardor bo'lishni yoqadi/o'chiradi."""
    permission_classes = [IsAuthenticated]

    def post(self, request, store_pk):
        store = Store.objects.filter(pk=store_pk).first()
        if store is None:
            return Response({'detail': "Do'kon topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        sub, created = StoreSubscription.objects.get_or_create(
            store=store, user=request.user, defaults={'is_enabled': True})
        if not created:
            sub.is_enabled = not sub.is_enabled
            sub.save(update_fields=['is_enabled'])
        return Response({'subscribed': sub.is_enabled})


class StoreAnnouncementCreateView(APIView):
    """POST — egasi do'kon sahifasida ko'rinadigan erkin matnli e'lon yozadi."""
    permission_classes = [IsAuthenticated]

    def post(self, request, store_pk):
        store = Store.objects.filter(pk=store_pk, owner=request.user).first()
        if store is None:
            return Response({'detail': "Do'kon topilmadi yoki ruxsat yo'q."},
                            status=status.HTTP_404_NOT_FOUND)
        text = (request.data.get('text') or '').strip()
        if not text:
            return Response({'detail': "E'lon matni majburiy."}, status=status.HTTP_400_BAD_REQUEST)
        update = create_store_update(
            store, 'announcement', text=text, image=request.FILES.get('image'))
        return Response(StoreUpdateSerializer(update, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)


# ── EGASI: buyurtma boshqaruvi (pickup ish oqimi) ──────────────────────────────
class StoreOrdersView(generics.ListAPIView):
    """GET — egasiga tegishli do'konlardagi buyurtmalar (mobil biznes paneli).

    ?fulfillment=pickup — faqat olib ketish buyurtmalari.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        qs = (Order.objects
              .filter(items__product__store__owner=self.request.user)
              .distinct().prefetch_related('items').order_by('-created_at'))
        if self.request.query_params.get('fulfillment') == 'pickup':
            qs = qs.filter(fulfillment_type='pickup')
        return qs


class StoreOrderStatusView(APIView):
    """POST {status} — egasi buyurtma holatini o'zgartiradi (yig'ilmoqda/tayyor/...).

    Pickup buyurtmasi to'lanmagan bo'lsa yig'ishni boshlab bo'lmaydi. 'ready'
    bo'lganda mijozga bildirishnoma yuboriladi.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        from delivery.models import can_transition
        order = Order.objects.filter(pk=order_id).first()
        if order is None:
            return Response({'detail': 'Buyurtma topilmadi.'}, status=status.HTTP_404_NOT_FOUND)
        if not order.items.filter(product__store__owner=request.user).exists():
            return Response({'detail': "Bu buyurtmani boshqarish huquqingiz yo'q."},
                            status=status.HTTP_403_FORBIDDEN)
        new_status = request.data.get('status', '')
        owner_allowed = {'accepted', 'preparing', 'ready', 'cancelled'}
        if order.is_pickup and not order.is_paid and new_status in {'preparing', 'ready'}:
            return Response({'detail': "Bu buyurtma hali to'lanmagan."},
                            status=status.HTTP_400_BAD_REQUEST)
        if new_status not in owner_allowed:
            return Response({'detail': "Bu holatni faqat haydovchi o'zgartiradi."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not can_transition(order.status, new_status, order.fulfillment_type):
            return Response({'detail': f"«{order.progress_label()}» dan bu holatga o'tib bo'lmaydi."},
                            status=status.HTTP_409_CONFLICT)
        order.status = new_status
        update_fields = ['status']
        if order.is_pickup and new_status == 'ready':
            order.ready_for_pickup_at = timezone.now()
            update_fields.append('ready_for_pickup_at')
        order.save(update_fields=update_fields)
        _push_order_status_safe(order)
        if order.is_pickup and new_status == 'ready':
            _notify_pickup_ready_safe(order)
        return Response(OrderSerializer(order, context={'request': request}).data)


class OrderConfirmPickupView(APIView):
    """POST — mijoz buyurtmani qo'lga olganini tasdiqlaydi (yakuniy holat).

    Faqat buyurtma egasi (mijoz), faqat pickup + 'ready' holatida.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = Order.objects.filter(pk=order_id).first()
        if order is None:
            return Response({'detail': 'Buyurtma topilmadi.'}, status=status.HTTP_404_NOT_FOUND)
        if order.user_id != request.user.id:
            return Response({'detail': "Bu buyurtmani tasdiqlash huquqingiz yo'q."},
                            status=status.HTTP_403_FORBIDDEN)
        if not order.can_customer_confirm_pickup:
            return Response({'detail': "Buyurtma hali tayyor emas yoki olib ketish buyurtmasi emas."},
                            status=status.HTTP_409_CONFLICT)
        order.status = 'delivered'
        order.customer_confirmed_at = timezone.now()
        order.save(update_fields=['status', 'customer_confirmed_at'])
        _push_order_status_safe(order)
        return Response(OrderSerializer(order, context={'request': request}).data)


def _push_order_status_safe(order):
    try:
        from delivery.realtime import push_order_status
        push_order_status(order)
    except Exception:
        pass


def _notify_pickup_ready_safe(order):
    try:
        from notifications.models import notify
        from django.urls import reverse
        url = reverse('delivery:order_detail', args=[order.id])
        notify(order.user, "Buyurtmangiz tayyor, olib keting! 🛍️", url, 'order')
    except Exception:
        pass
