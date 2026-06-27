from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'category', 'text', 'is_read', 'created_at')
    list_filter = ('category', 'is_read')
    search_fields = ('recipient__phone', 'recipient__name', 'text')
    readonly_fields = ('created_at',)
