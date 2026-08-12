from django.contrib import admin

from .models import (AgentAuditLog, AgentTask, AgentUsage, PendingAction,
                     SelectionSet, UnansweredQuery)


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


# ═══════════════════════════════════════════════════════════════════════════
#  AGENT MODELLARI — asosan KUZATUV uchun (o'qish rejimida)
# ═══════════════════════════════════════════════════════════════════════════

@admin.register(AgentTask)
class AgentTaskAdmin(admin.ModelAdmin):
    list_display = ('goal', 'state', 'status', 'user', 'session_key',
                    'updated_at', 'expires_at')
    list_filter = ('status', 'goal')
    search_fields = ('goal', 'session_key', 'user__phone', 'user__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(SelectionSet)
class SelectionSetAdmin(admin.ModelAdmin):
    list_display = ('ref', 'section', 'user', 'created_at', 'expires_at')
    list_filter = ('section',)
    search_fields = ('ref', 'session_key', 'user__phone')
    readonly_fields = ('ref', 'created_at')


@admin.register(PendingAction)
class PendingActionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'user', 'status', 'amount', 'created_at',
                    'confirmed_at', 'expires_at')
    list_filter = ('status', 'section')
    search_fields = ('user__phone', 'user__name', 'action')
    readonly_fields = ('id', 'section', 'action', 'payload', 'summary_card',
                       'amount', 'result', 'created_at', 'confirmed_at', 'expires_at')
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        # Tasdiq amallari faqat agent orqali yaratiladi — qo'lda emas.
        return False


@admin.register(AgentAuditLog)
class AgentAuditLogAdmin(admin.ModelAdmin):
    list_display = ('section', 'action', 'result_status', 'user',
                    'duration_ms', 'created_at')
    list_filter = ('result_status', 'section')
    search_fields = ('action', 'user__phone', 'error')
    readonly_fields = ('user', 'session_key', 'task_id', 'section', 'action',
                       'params', 'result_status', 'error', 'duration_ms',
                       'llm_model', 'tokens_in', 'tokens_out', 'created_at')
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AgentUsage)
class AgentUsageAdmin(admin.ModelAdmin):
    # proposals — taklif qilingan, mutations — haqiqatda bajarilgan (ikkisi boshqa).
    list_display = ('user', 'date', 'llm_calls', 'tool_calls', 'proposals',
                    'mutations', 'total_amount')
    list_filter = ('date',)
    search_fields = ('user__phone', 'user__name')
    readonly_fields = ('user', 'date', 'llm_calls', 'tool_calls', 'proposals',
                       'mutations', 'total_amount')

    def has_add_permission(self, request):
        return False
