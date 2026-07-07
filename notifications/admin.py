from django.contrib import admin
from .models import Notification, DeviceToken


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'category', 'text', 'is_read', 'created_at')
    list_filter = ('category', 'is_read')
    search_fields = ('recipient__phone', 'recipient__name', 'text')
    readonly_fields = ('created_at',)


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform', 'is_active', 'last_seen_at', 'created_at')
    list_filter = ('platform', 'is_active')
    search_fields = ('user__phone', 'user__name', 'token')
    readonly_fields = ('created_at', 'last_seen_at')
