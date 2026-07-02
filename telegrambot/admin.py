from django.contrib import admin

from .models import TelegramLink


@admin.register(TelegramLink)
class TelegramLinkAdmin(admin.ModelAdmin):
    list_display = ('phone', 'chat_id', 'telegram_username', 'linked_at')
    search_fields = ('phone', 'telegram_username', 'chat_id')
    readonly_fields = ('linked_at',)
