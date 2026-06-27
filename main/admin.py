from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import (
    User, OTPCode, Ad, AdImage,
    Neighborhood, ChatRoom, ChatMessage, ChatAdmin, ChatMember, MessageReaction,
    Booking, JobAd, ResumeAd, UtilityPayment,
    BoostPayment,
    Poll, PollOption, PollVote, PollComment,
    HelpRequest, HelpVolunteer,
    AdFavorite, AdReport, AdInquiry, SearchQuery,
)


@admin.register(AdReport)
class AdReportAdmin(admin.ModelAdmin):
    list_display = ('ad', 'reason', 'reporter', 'is_resolved', 'created_at')
    list_filter = ('reason', 'is_resolved')


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ('term', 'count', 'updated_at')
    search_fields = ('term',)


admin.site.register(AdFavorite)
admin.site.register(AdInquiry)


# ── COMMUNITY: Polls & Help (registered at module end) ───────────────────────
class PollOptionInline(admin.TabularInline):
    model = PollOption
    extra = 2


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ('question', 'creator', 'neighborhood', 'poll_type', 'is_active', 'expires_at', 'created_at')
    list_filter = ('poll_type', 'is_active', 'is_anonymous')
    search_fields = ('question',)
    inlines = [PollOptionInline]


@admin.register(HelpRequest)
class HelpRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'kind', 'category', 'status', 'is_urgent', 'creator', 'created_at')
    list_filter = ('kind', 'category', 'status', 'is_urgent')
    search_fields = ('title', 'description')


admin.site.register(MessageReaction)
admin.site.register(PollVote)
admin.site.register(PollComment)
admin.site.register(HelpVolunteer)


# ── USER ─────────────────────────────────────────────────────────────────────
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Custom-user forms so admin add/change pages work with phone-based User
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    list_display = ('phone', 'name', 'role', 'is_active', 'is_staff', 'created_at')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('phone', 'name', 'email')
    ordering = ('-created_at',)
    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('Shaxsiy', {'fields': ('name', 'username', 'email', 'bio', 'avatar', 'avatar_url')}),
        ('Ruxsatlar', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ("Qo'shimcha", {'fields': ('rating',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'password1', 'password2', 'role'),
        }),
    )


# ── OTP ──────────────────────────────────────────────────────────────────────
@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ('phone', 'code', 'used', 'expires_at', 'created_at')
    list_filter = ('used',)
    search_fields = ('phone',)


# ── ADS ──────────────────────────────────────────────────────────────────────
class AdImageInline(admin.TabularInline):
    model = AdImage
    extra = 0


@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'status', 'price', 'is_boosted', 'venue_booking_enabled', 'created_at')
    list_filter = ('status', 'category', 'is_boosted', 'venue_booking_enabled')
    search_fields = ('title', 'user__phone', 'user__name')
    inlines = [AdImageInline]
    readonly_fields = ('views', 'created_at', 'updated_at')
    list_editable = ('is_boosted', 'venue_booking_enabled')


# ── BOOKING ──────────────────────────────────────────────────────────────────
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('ad', 'buyer', 'owner', 'status', 'payment_status', 'total_amount', 'start_date', 'end_date', 'created_at')
    list_filter = ('status', 'payment_status')
    search_fields = ('ad__title', 'buyer__phone', 'owner__phone')
    readonly_fields = ('created_at', 'updated_at')


# ── CHAT ─────────────────────────────────────────────────────────────────────
@admin.register(Neighborhood)
class NeighborhoodAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('neighborhood', 'created_at')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('room', 'is_admin_message', 'text', 'created_at')
    list_filter = ('room', 'is_admin_message')
    search_fields = ('user__phone', 'text')


@admin.register(ChatAdmin)
class ChatAdminAdmin(admin.ModelAdmin):
    list_display = ('neighborhood', 'user', 'appointed_at')
    list_filter = ('neighborhood',)
    search_fields = ('user__phone', 'user__name', 'neighborhood__name')
    autocomplete_fields = ['user', 'neighborhood']


@admin.register(ChatMember)
class ChatMemberAdmin(admin.ModelAdmin):
    list_display = ('room', 'user', 'is_approved', 'is_banned', 'joined_at')
    list_filter = ('room', 'is_approved', 'is_banned')
    search_fields = ('user__phone', 'user__name')
    list_editable = ('is_approved', 'is_banned')
    readonly_fields = ('joined_at', 'approved_at')


# ── JOBS & RESUMES ────────────────────────────────────────────────────────────
@admin.register(JobAd)
class JobAdAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'user', 'job_type', 'status', 'created_at')
    list_filter = ('status', 'job_type')
    search_fields = ('title', 'company', 'user__phone', 'user__name')
    readonly_fields = ('views', 'created_at', 'updated_at')


@admin.register(ResumeAd)
class ResumeAdAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'experience', 'status', 'created_at')
    list_filter = ('status', 'experience')
    search_fields = ('title', 'user__phone', 'user__name')
    readonly_fields = ('views', 'created_at', 'updated_at')


# ── UTILITY ──────────────────────────────────────────────────────────────────
@admin.register(UtilityPayment)
class UtilityPaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'service', 'amount', 'period', 'status', 'paid_at')
    list_filter = ('service', 'status', 'period')
    search_fields = ('user__phone', 'user__name', 'note')
    readonly_fields = ('created_at',)


# ── BOOST PAYMENTS ───────────────────────────────────────────────────────────
@admin.register(BoostPayment)
class BoostPaymentAdmin(admin.ModelAdmin):
    list_display = ('ad', 'user', 'plan', 'amount', 'status', 'starts_at', 'expires_at')
    list_filter = ('status', 'plan')
    search_fields = ('ad__title', 'user__phone')
    readonly_fields = ('starts_at', 'expires_at')
