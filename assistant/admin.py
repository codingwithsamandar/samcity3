from django.contrib import admin

from .models import UnansweredQuery


@admin.register(UnansweredQuery)
class UnansweredQueryAdmin(admin.ModelAdmin):
    """Javobsiz savollar — eng ko'p so'ralganidan boshlab ko'rinadi.

    Bu yerdan odamlar nima so'raganini ko'rib, engine.py yoki knowledge.py ga
    kalit so'z/qo'llanma qo'shib, "hal qilingan" deb belgilaysiz.
    """
    list_display = ('text', 'count', 'resolved', 'last_seen', 'created_at')
    list_filter = ('resolved',)
    search_fields = ('text', 'normalized')
    ordering = ('-count', '-last_seen')
    readonly_fields = ('normalized', 'text', 'count', 'created_at', 'last_seen')
    actions = ('mark_resolved', 'mark_unresolved')

    @admin.action(description="Hal qilingan deb belgilash")
    def mark_resolved(self, request, queryset):
        n = queryset.update(resolved=True)
        self.message_user(request, f"{n} ta savol hal qilingan deb belgilandi.")

    @admin.action(description="Hal qilinmagan deb belgilash")
    def mark_unresolved(self, request, queryset):
        queryset.update(resolved=False)
