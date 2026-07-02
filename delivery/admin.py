from django import forms
from django.contrib import admin
from main.admin_widgets import LatLngPickerWidget
from .models import (
    DeliveryCategory, Store, StoreImage, Product, ProductImage, Cart, CartItem,
    Order, OrderItem, DeliveryDriver, StoreUpdate, StoreSubscription,
    StoreChatThread, StoreChatMessage,
)


# ── DELIVERY CATEGORY ─────────────────────────────────────────────────────────
@admin.register(DeliveryCategory)
class DeliveryCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


# ── STORE ─────────────────────────────────────────────────────────────────────
class StoreAdminForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = '__all__'
        widgets = {'latitude': LatLngPickerWidget}


class StoreImageInline(admin.TabularInline):
    model = StoreImage
    extra = 0
    max_num = StoreImage.MAX_IMAGES


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    form = StoreAdminForm
    list_display = ('name', 'owner', 'category', 'phone', 'working_hours', 'pickup_enabled', 'is_active', 'created_at')
    list_filter = ('is_active', 'pickup_enabled', 'category')
    search_fields = ('name', 'owner__phone', 'owner__name', 'address', 'phone')
    list_editable = ('pickup_enabled', 'is_active')
    readonly_fields = ('created_at',)
    inlines = [StoreImageInline]


@admin.register(StoreImage)
class StoreImageAdmin(admin.ModelAdmin):
    list_display = ('store', 'image', 'created_at')
    search_fields = ('store__name',)


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
    list_display = ('id', 'user', 'phone', 'total', 'fulfillment_type', 'status', 'driver', 'payment_status', 'created_at')
    list_filter = ('fulfillment_type', 'status', 'payment_status', 'payment_method')
    search_fields = ('user__phone', 'phone', 'address')
    readonly_fields = ('created_at', 'ready_for_pickup_at', 'customer_confirmed_at')
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


# ── STORE UPDATE / SUBSCRIPTION (yangiliklar + bildirishnoma obunasi) ──────────
@admin.register(StoreUpdate)
class StoreUpdateAdmin(admin.ModelAdmin):
    list_display = ('store', 'update_type', 'product', 'created_at')
    list_filter = ('update_type',)
    search_fields = ('store__name', 'text', 'product__name')
    readonly_fields = ('created_at',)


@admin.register(StoreSubscription)
class StoreSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('store', 'user', 'is_enabled', 'created_at')
    list_filter = ('is_enabled',)
    search_fields = ('store__name', 'user__phone', 'user__name')
    readonly_fields = ('created_at',)


# ── STORE CHAT (3.1-bosqich skeleti) ────────────────────────────────────────────
@admin.register(StoreChatThread)
class StoreChatThreadAdmin(admin.ModelAdmin):
    list_display = ('store', 'customer', 'created_at')
    search_fields = ('store__name', 'customer__phone', 'customer__name')


@admin.register(StoreChatMessage)
class StoreChatMessageAdmin(admin.ModelAdmin):
    list_display = ('thread', 'sender', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('text',)
