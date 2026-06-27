from django.contrib import admin
from .models import DeliveryCategory, Store, Product, ProductImage, Cart, CartItem, Order, OrderItem, DeliveryDriver


# ── DELIVERY CATEGORY ─────────────────────────────────────────────────────────
@admin.register(DeliveryCategory)
class DeliveryCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


# ── STORE ─────────────────────────────────────────────────────────────────────
@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'category', 'phone', 'is_active', 'created_at')
    list_filter = ('is_active', 'category')
    search_fields = ('name', 'owner__phone', 'owner__name', 'address', 'phone')
    list_editable = ('is_active',)
    readonly_fields = ('created_at',)


# ── PRODUCT ───────────────────────────────────────────────────────────────────
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    max_num = 4


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'store', 'price', 'stock', 'is_available', 'created_at')
    list_filter = ('is_available', 'store')
    search_fields = ('name', 'store__name')
    list_editable = ('is_available',)
    readonly_fields = ('created_at',)
    inlines = [ProductImageInline]


# ── PRODUCT IMAGE ─────────────────────────────────────────────────────────────
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image')
    search_fields = ('product__name',)


# ── CART ──────────────────────────────────────────────────────────────────────
class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('product', 'quantity', 'created_at')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_total_items', 'get_total_quantity', 'updated_at')
    search_fields = ('user__phone', 'user__name')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [CartItemInline]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity', 'created_at')
    search_fields = ('product__name', 'cart__user__phone')
    readonly_fields = ('created_at',)


# ── ORDER ───────────────────────────────────────────────────────────────────────
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'store_name', 'price', 'quantity')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'phone', 'total', 'status', 'driver', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_status', 'payment_method')
    search_fields = ('user__phone', 'phone', 'address')
    readonly_fields = ('created_at',)
    list_editable = ('status',)
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'store_name', 'price', 'quantity', 'order')
    search_fields = ('product_name', 'store_name')


@admin.register(DeliveryDriver)
class DeliveryDriverAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'vehicle_type', 'vehicle_number', 'is_available', 'is_active', 'created_at')
    list_filter = ('vehicle_type', 'is_available', 'is_active')
    search_fields = ('full_name', 'phone', 'user__phone')
    list_editable = ('is_available', 'is_active')
