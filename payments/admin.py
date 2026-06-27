from django.contrib import admin
from .models import Provider, ServicePayment, Transaction


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'amount', 'phone', 'region', 'is_active')
    list_filter = ('category', 'is_active', 'region')
    search_fields = ('name', 'description', 'phone')
    list_editable = ('amount', 'is_active')


@admin.register(ServicePayment)
class ServicePaymentAdmin(admin.ModelAdmin):
    list_display = ('provider_name', 'category', 'user', 'payer_name', 'amount', 'status', 'paid_at')
    list_filter = ('category', 'status')
    search_fields = ('provider_name', 'payer_name', 'user__phone', 'card_last4')
    readonly_fields = ('created_at', 'paid_at')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('provider', 'provider_transaction_id', 'target_type', 'target_id',
                    'amount', 'state', 'created_at')
    list_filter = ('provider', 'state', 'target_type')
    search_fields = ('provider_transaction_id', 'target_id')
    readonly_fields = ('created_at', 'performed_at', 'canceled_at')
