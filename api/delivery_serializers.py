"""Delivery (yetkazish) moduli serializerlari."""
from rest_framework import serializers

from delivery.models import Store, Product, ProductImage, Cart, CartItem, Order, OrderItem


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

    class Meta:
        model = Product
        fields = ('id', 'name', 'description', 'price', 'stock',
                  'is_available', 'images', 'cover')

    def get_price(self, obj):
        return int(obj.price)

    def get_cover(self, obj):
        first = obj.images.all().first()
        return _abs(self.context.get('request'), first.image) if first else None


class StoreListSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()
    category = serializers.CharField(source='category.name', default=None, read_only=True)
    product_count = serializers.IntegerField(source='products.count', read_only=True)

    class Meta:
        model = Store
        fields = ('id', 'name', 'description', 'address', 'phone',
                  'logo', 'category', 'product_count')

    def get_logo(self, obj):
        return _abs(self.context.get('request'), obj.logo)


class StoreDetailSerializer(StoreListSerializer):
    products = serializers.SerializerMethodField()

    class Meta(StoreListSerializer.Meta):
        fields = StoreListSerializer.Meta.fields + ('latitude', 'longitude', 'products')

    def get_products(self, obj):
        qs = obj.products.filter(is_available=True).prefetch_related('images')
        return ProductSerializer(qs, many=True, context=self.context).data


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

    class Meta:
        model = Order
        fields = ('id', 'full_name', 'phone', 'address', 'note',
                  'subtotal', 'delivery_fee', 'total', 'status', 'status_display',
                  'payment_method', 'payment_status', 'card_last4', 'card_brand',
                  'items', 'created_at')


class CheckoutSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=30)
    address = serializers.CharField(max_length=300)
    note = serializers.CharField(required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(choices=['card', 'cash'], default='card')
    # Karta (demo) — to'liq raqam/CVV SAQLANMAYDI
    card_number = serializers.CharField(required=False, allow_blank=True)
    expiry = serializers.CharField(required=False, allow_blank=True)
    cvv = serializers.CharField(required=False, allow_blank=True)
