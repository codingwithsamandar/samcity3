"""Delivery (yetkazish) API view'lari: do'konlar, mahsulotlar, savat, buyurtma."""
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import (
    api_view, permission_classes as perm, throttle_classes,
)
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from delivery.models import (
    Store, Product, Cart, CartItem, Order, OrderItem, DeliveryCategory,
)
from .throttles import CheckoutThrottle
from .delivery_serializers import (
    StoreListSerializer, StoreDetailSerializer, ProductSerializer,
    CartSerializer, OrderSerializer, CheckoutSerializer,
)

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
    # To'lov: 'cash' — yetkazishda naqd; 'card' — onlayn (Payme/Click) orqali,
    # buyurtma yaratilgach `/api/payments/initiate/` bilan to'lanadi. Ikkala
    # holatda ham buyurtma 'unpaid' yaratiladi (karta ma'lumoti bu yerda olinmaydi).
    payment_status = 'unpaid'
    card_last4 = card_brand = ''

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
        # (multi-store split). Har biri o'z yetkazish narxiga ega.
        groups = {}
        for it in items:
            p = locked[it.product_id]
            groups.setdefault(p.store_id, []).append((it, p))

        for store_id, group in groups.items():
            g_subtotal = int(sum(p.price * it.quantity for it, p in group))
            order = Order.objects.create(
                user=request.user,
                full_name=data.get('full_name') or (request.user.name or ''),
                phone=data['phone'], address=data['address'], note=data.get('note', ''),
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
            category=cat, is_active=True,
        )
        return Response(StoreDetailSerializer(store, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)


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
        product = Product.objects.create(
            store=store, name=name, price=price, stock=max(stock, 0),
            description=(request.data.get('description') or '').strip(),
            is_available=True,
        )
        return Response(ProductSerializer(product, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)
