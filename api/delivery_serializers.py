"""Delivery (yetkazish) moduli serializerlari."""
from django.conf import settings
from rest_framework import serializers

from delivery.models import (
    Store, StoreImage, Product, ProductImage, Cart, CartItem, Order, OrderItem,
    StoreUpdate, StoreSubscription,
)


def _abs(request, field):
    if not field:
        return None
    url = field.url
    return request.build_absolute_uri(url) if request else url


class ProductImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ('id', 'image')

    def get_image(self, obj):
        return _abs(self.context.get('request'), obj.image)


class ProductSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)
    cover = serializers.SerializerMethodField()
    # Mahsulot do'koni olib ketish (pickup) rejimidami — savat/checkout uchun.
    pickup = serializers.BooleanField(source='store.pickup_enabled', read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'description', 'price', 'stock',
                  'is_available', 'images', 'cover', 'restock_at', 'pickup')

    def get_price(self, obj):
        return int(obj.price)

    def get_cover(self, obj):
        first = obj.images.all().first()
        return _abs(self.context.get('request'), first.image) if first else None


class StoreImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = StoreImage
        fields = ('id', 'image')

    def get_image(self, obj):
        return _abs(self.context.get('request'), obj.image)


class StoreUpdateSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    update_type_display = serializers.CharField(source='get_update_type_display', read_only=True)
    product_name = serializers.CharField(source='product.name', default=None, read_only=True)
    old_price = serializers.SerializerMethodField()
    new_price = serializers.SerializerMethodField()

    class Meta:
        model = StoreUpdate
        fields = ('id', 'update_type', 'update_type_display', 'text', 'image',
                  'product', 'product_name', 'old_price', 'new_price', 'created_at')

    def get_image(self, obj):
        return _abs(self.context.get('request'), obj.image)

    def get_old_price(self, obj):
        return int(obj.old_price) if obj.old_price is not None else None

    def get_new_price(self, obj):
        return int(obj.new_price) if obj.new_price is not None else None


class StoreListSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()
    category = serializers.CharField(source='category.name', default=None, read_only=True)
    product_count = serializers.IntegerField(source='products.count', read_only=True)
    cart_enabled = serializers.SerializerMethodField()

    class Meta:
        model = Store
        fields = ('id', 'name', 'description', 'address', 'phone', 'working_hours',
                  'logo', 'category', 'product_count', 'cart_enabled', 'pickup_enabled')

    def get_logo(self, obj):
        return _abs(self.context.get('request'), obj.logo)

    def get_cart_enabled(self, obj):
        # Savat/checkout: pickup yoqilgan do'konda (yoki global flag) ochiladi.
        return bool(obj.pickup_enabled or settings.DELIVERY_CART_ENABLED)


class StoreDetailSerializer(StoreListSerializer):
    products = serializers.SerializerMethodField()
    gallery = StoreImageSerializer(source='images', many=True, read_only=True)
    owner_photo = serializers.SerializerMethodField()
    updates = serializers.SerializerMethodField()
    subscribed = serializers.SerializerMethodField()

    class Meta(StoreListSerializer.Meta):
        fields = StoreListSerializer.Meta.fields + (
            'latitude', 'longitude', 'products', 'gallery',
            'owner_bio', 'owner_photo', 'updates', 'subscribed',
        )

    def get_products(self, obj):
        qs = obj.products.filter(is_available=True).prefetch_related('images')
        return ProductSerializer(qs, many=True, context=self.context).data

    def get_owner_photo(self, obj):
        return _abs(self.context.get('request'), obj.owner_photo)

    def get_updates(self, obj):
        qs = obj.updates.select_related('product')[:20]
        return StoreUpdateSerializer(qs, many=True, context=self.context).data

    def get_subscribed(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        return StoreSubscription.objects.filter(store=obj, user=user, is_enabled=True).exists()


# ── Cart ────────────────────────────────────────────────────────────────────
class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ('id', 'product', 'quantity', 'line_total')

    def get_line_total(self, obj):
        return int(obj.get_line_total())


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(source='get_total_items', read_only=True)
    total_quantity = serializers.IntegerField(source='get_total_quantity', read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ('id', 'items', 'total_items', 'total_quantity', 'subtotal')

    def get_subtotal(self, obj):
        return int(obj.get_subtotal())


# ── Order ───────────────────────────────────────────────────────────────────
class OrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ('id', 'product_name', 'store_name', 'price', 'quantity', 'line_total')

    def get_price(self, obj):
        return int(obj.price)

    def get_line_total(self, obj):
        return int(obj.get_line_total())


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    # Pickup buyurtmalari uchun holat nomi boshqacha (olib ketish atamalari).
    progress_label = serializers.CharField(read_only=True)
    can_confirm_pickup = serializers.BooleanField(source='can_customer_confirm_pickup', read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'full_name', 'phone', 'address', 'note',
                  'subtotal', 'delivery_fee', 'total', 'status', 'status_display',
                  'progress_label', 'fulfillment_type', 'pickup_at',
                  'ready_for_pickup_at', 'customer_confirmed_at', 'can_confirm_pickup',
                  'payment_method', 'payment_status', 'card_last4', 'card_brand',
                  'items', 'created_at')


class CheckoutSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=30)
    # Manzil pickup buyurtmasida majburiy emas (view'da tekshiriladi).
    address = serializers.CharField(max_length=300, required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(choices=['card', 'cash'], default='card')
    pickup_at = serializers.DateTimeField(required=False, allow_null=True)
    # Karta (demo) — to'liq raqam/CVV SAQLANMAYDI
    card_number = serializers.CharField(required=False, allow_blank=True)
    expiry = serializers.CharField(required=False, allow_blank=True)
    cvv = serializers.CharField(required=False, allow_blank=True)
