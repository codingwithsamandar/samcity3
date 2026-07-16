from django import forms
from django.contrib import admin, messages
from django.utils.safestring import mark_safe
from main.admin_widgets import LatLngPickerWidget
from .models import (
    DeliveryCategory, Store, StoreImage, Product, ProductImage, Cart, CartItem,
    Order, OrderItem, DeliveryDriver, DriverReview, StoreUpdate, StoreSubscription,
    StoreChatThread, StoreChatMessage, StoreRequest, CatalogProduct,
)


@admin.register(DriverReview)
class DriverReviewAdmin(admin.ModelAdmin):
    list_display = ('driver', 'rating', 'user', 'created_at')
    list_filter = ('rating',)
    search_fields = ('driver__full_name', 'user__phone', 'comment')
    readonly_fields = ('created_at',)


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
    list_display = ('name', 'store_type', 'neighborhood', 'owner', 'category', 'phone', 'pickup_enabled', 'is_active', 'created_at')
    list_filter = ('store_type', 'is_active', 'pickup_enabled', 'neighborhood', 'category')
    search_fields = ('name', 'owner__phone', 'owner__name', 'address', 'phone')
    list_editable = ('is_active',)
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
    list_display = ('name', 'store', 'catalog_product', 'is_custom_flag', 'price',
                    'stock', 'is_available', 'created_at')
    list_filter = ('is_available', 'store', ('catalog_product', admin.EmptyFieldListFilter))
    search_fields = ('name', 'store__name', 'catalog_product__name')
    list_editable = ('is_available',)
    readonly_fields = ('created_at',)
    autocomplete_fields = ('store', 'catalog_product')
    inlines = [ProductImageInline]
    actions = ('promote_to_catalog',)

    @admin.display(description='Custom', boolean=True)
    def is_custom_flag(self, obj):
        return obj.is_custom

    @admin.action(description="Katalogga ko'chirish (promote → CatalogProduct)")
    def promote_to_catalog(self, request, queryset):
        """Tanlangan CUSTOM mahsulotlardan katalog yozuvi yaratadi va manbani
        yangi katalogga bog'laydi. Allaqachon bog'langanlari o'tkazib yuboriladi."""
        from django.core.files.base import ContentFile
        created = skipped = 0
        for p in queryset.select_related('store'):
            if p.catalog_product_id is not None:
                skipped += 1
                continue
            cat = CatalogProduct.objects.create(
                name=p.name, description=p.description,
                category=(p.store.category if p.store_id else None),
                created_by=request.user, promoted_from=p,
            )
            first = p.images.first()
            if first and first.image:
                try:
                    fname = first.image.name.split('/')[-1]
                    with first.image.open('rb') as fh:
                        cat.image.save(fname, ContentFile(fh.read()), save=True)
                except Exception:
                    pass
            p.catalog_product = cat
            p.save(update_fields=['catalog_product'])
            created += 1
        self.message_user(
            request,
            f"{created} ta mahsulot katalogga ko'chirildi"
            + (f"; {skipped} ta o'tkazib yuborildi (allaqachon bog'langan)." if skipped else "."),
            messages.SUCCESS if created else messages.WARNING)


@admin.register(CatalogProduct)
class CatalogProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'category', 'unit', 'suggested_price', 'is_active',
                    'store_count', 'image_tag', 'created_at')
    # ('image', EmptyFieldListFilter) — "rasmsiz mahsulotlar" tez filtri.
    # ('suggested_price', EmptyFieldListFilter) — "tavsiya narxsiz" tez filtri.
    list_filter = ('is_active', 'category', 'brand', 'unit',
                   ('image', admin.EmptyFieldListFilter),
                   ('suggested_price', admin.EmptyFieldListFilter))
    search_fields = ('name', 'brand')
    list_editable = ('suggested_price', 'is_active')
    autocomplete_fields = ('category',)
    readonly_fields = ('created_by', 'promoted_from', 'created_at', 'updated_at', 'image_tag')
    change_list_template = 'admin/delivery/catalogproduct/change_list.html'

    def get_queryset(self, request):
        # store_count ustuni uchun N+1 o'rniga bitta annotate so'rovi.
        from django.db.models import Count
        return super().get_queryset(request).annotate(
            _store_count=Count('store_products', distinct=True))

    @admin.display(description='Rasm')
    def image_tag(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" style="height:40px;border-radius:6px;">')
        return '—'

    @admin.display(description="Do'konlarda", ordering='_store_count')
    def store_count(self, obj):
        return obj._store_count

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    # ── Hisobot: rasm qamrovi + salomatlik (admin ichida) ────────────────────
    def get_urls(self):
        from django.urls import path
        return [
            path('report/', self.admin_site.admin_view(self.report_view),
                 name='delivery_catalogproduct_report'),
            path('missing-images.csv', self.admin_site.admin_view(self.missing_images_csv),
                 name='delivery_catalogproduct_missing_csv'),
        ] + super().get_urls()

    def report_view(self, request):
        from django.template.response import TemplateResponse
        from delivery.catalog_stats import catalog_stats, missing_image_products
        ctx = {
            **self.admin_site.each_context(request),
            'title': 'Katalog hisoboti',
            'stats': catalog_stats(),
            'missing': missing_image_products()[:200],
            'opts': self.model._meta,
        }
        return TemplateResponse(request, 'admin/delivery/catalogproduct/report.html', ctx)

    def missing_images_csv(self, request):
        import csv
        from django.http import HttpResponse
        from delivery.catalog_stats import missing_image_products
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="catalog_missing_images.csv"'
        response.write('\ufeff')  # BOM — Excel'da UTF-8 to'g'ri ochilishi uchun
        writer = csv.writer(response)
        writer.writerow(['id', 'name', 'brand', 'category', 'unit', 'is_active'])
        for p in missing_image_products():
            writer.writerow([p.pk, p.name, p.brand,
                             p.category.name if p.category else '', p.unit, p.is_active])
        return response


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


# ── MAHALLA DO'KON ARIZASI (tasdiqlash/rad etish) ───────────────────────────────
@admin.register(StoreRequest)
class StoreRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'neighborhood', 'status', 'created_store', 'created_at')
    list_filter = ('status', 'neighborhood')
    search_fields = ('name', 'user__phone', 'user__name', 'address')
    readonly_fields = ('created_store', 'reviewed_by', 'reviewed_at', 'created_at')
    actions = ('approve_requests', 'reject_requests')

    @admin.action(description="✅ Tasdiqlash — mahalla do'konini yaratish")
    def approve_requests(self, request, queryset):
        n = 0
        for req in queryset.filter(status='pending'):
            req.approve(reviewer=request.user)
            n += 1
        self.message_user(request, f"{n} ta ariza tasdiqlandi va do'kon yaratildi.", messages.SUCCESS)

    @admin.action(description="✕ Rad etish")
    def reject_requests(self, request, queryset):
        n = 0
        for req in queryset.filter(status='pending'):
            req.reject(reviewer=request.user)
            n += 1
        self.message_user(request, f"{n} ta ariza rad etildi.", messages.WARNING)
