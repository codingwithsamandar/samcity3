from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .admin_widgets import LatLngPickerWidget
from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import (
    User, OTPCode, Ad, AdImage,
    Neighborhood, ChatAdmin,
    Booking, JobAd, ResumeAd, UtilityPayment,
    BoostPayment,
    Poll, PollOption, PollVote, PollComment,
    HelpRequest, HelpVolunteer,
    AdFavorite, AdReport, AdInquiry, SearchQuery,
    NeighborhoodAnnouncement, CitizenRequest,
    District, DistrictAdmin, DistrictAnnouncement,
    AdCampaign, AdCampaignDelivery,
)
from django.contrib import messages as admin_messages


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


class HelpRequestAdminForm(forms.ModelForm):
    class Meta:
        model = HelpRequest
        fields = '__all__'
        widgets = {'latitude': LatLngPickerWidget}


@admin.register(HelpRequest)
class HelpRequestAdmin(admin.ModelAdmin):
    form = HelpRequestAdminForm
    list_display = ('title', 'kind', 'category', 'status', 'is_urgent', 'creator', 'created_at')
    list_filter = ('kind', 'category', 'status', 'is_urgent')
    search_fields = ('title', 'description')


admin.site.register(PollVote)
admin.site.register(PollComment)
admin.site.register(HelpVolunteer)


# ── USER ─────────────────────────────────────────────────────────────────────
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Custom-user forms so admin add/change pages work with phone-based User
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    list_display = ('phone', 'name', 'role', 'gender', 'birth_date', 'is_active', 'is_staff', 'created_at')
    list_filter = ('role', 'gender', 'is_active', 'is_staff')
    search_fields = ('phone', 'name', 'email')
    ordering = ('-created_at',)
    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('Shaxsiy', {'fields': ('name', 'username', 'email', 'bio', 'avatar', 'avatar_url',
                                'gender', 'birth_date')}),
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


class AdAdminForm(forms.ModelForm):
    class Meta:
        model = Ad
        fields = '__all__'
        widgets = {'latitude': LatLngPickerWidget}


@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    form = AdAdminForm
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
from django import forms
from django.utils.safestring import mark_safe


class PolygonEditorWidget(forms.Textarea):
    """Adminda mahalla chegarasini xaritada chizib/tahrirlab beradigan widget.

    Pastdagi JSON maydon (chegara nuqtalari) Leaflet xaritasi bilan sinxron.
    """
    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        attrs.setdefault('id', 'id_%s' % name)
        attrs['style'] = 'width:100%;font-family:monospace;font-size:12px;height:90px;'
        textarea = super().render(name, value, attrs, renderer)
        return mark_safe(
            '<div class="mahalla-poly-editor">'
            '<div id="mahallaEditorMap" style="height:440px;border:1px solid #ccc;'
            'border-radius:8px;margin:.4rem 0;"></div>'
            '<p style="font-size:12px;color:#555;margin:.2rem 0 .4rem;">'
            "Chizish/tahrirlash: chap-yuqoridagi ✐ bilan yangi poligon chizing yoki "
            "mavjud tugunlarni torting. Maydon avtomatik yangilanadi.</p>"
            '<details><summary style="cursor:pointer;font-size:12px;color:#666;">'
            'Chegara (JSON)</summary>' + textarea + '</details></div>'
        )

    class Media:
        css = {'all': (
            'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css',
            'https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.min.css',
        )}
        js = (
            'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.min.js',
            'admin/js/mahalla_polygon_editor.js',
        )


# ── TUMAN (District) + hokim ─────────────────────────────────────────────────
class DistrictAdminInline(admin.TabularInline):
    model = DistrictAdmin
    extra = 1
    autocomplete_fields = ['user']


@admin.register(District)
class DistrictAdminModel(admin.ModelAdmin):
    list_display = ('name', 'head_name', 'head_phone', 'mahalla_count', 'created_at')
    search_fields = ('name', 'head_name', 'head_phone')
    inlines = [DistrictAdminInline]

    @admin.display(description='Mahallalar')
    def mahalla_count(self, obj):
        return obj.neighborhoods.count()


@admin.register(DistrictAdmin)
class DistrictAdminAdmin(admin.ModelAdmin):
    list_display = ('district', 'user', 'appointed_at')
    list_filter = ('district',)
    search_fields = ('user__phone', 'user__name', 'district__name')
    autocomplete_fields = ['user', 'district']


@admin.register(DistrictAnnouncement)
class DistrictAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'district', 'created_by', 'recipients_count', 'created_at')
    list_filter = ('district',)
    search_fields = ('title', 'text', 'district__name')
    readonly_fields = ('created_at', 'recipients_count')
    autocomplete_fields = ['district', 'created_by']

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        # Admin orqali YANGI tuman e'loni ham butun tuman aholisiga borsin.
        if not change:
            from django.urls import reverse
            from .community_views import _notify_district
            sent = _notify_district(
                obj.district, f"🏛️ Tuman e'loni: {obj.title[:60]}",
                reverse('hokim_panel'), exclude_user=request.user)
            obj.recipients_count = sent
            obj.save(update_fields=['recipients_count'])
            self.message_user(request, f"{sent} ta aholiga bildirishnoma yuborildi.",
                              level=admin_messages.SUCCESS)


# ── REKLAMA KAMPANIYASI ──────────────────────────────────────────────────────
@admin.register(AdCampaign)
class AdCampaignAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'send_to_all', 'gender', 'age_range', 'neighborhood',
                    'district', 'role', 'target_count', 'audience_preview', 'sent_count',
                    'created_at')
    list_filter = ('status', 'send_to_all', 'gender', 'role', 'district', 'neighborhood')
    search_fields = ('title', 'text')
    autocomplete_fields = ['neighborhood', 'district']
    readonly_fields = ('status', 'sent_count', 'sent_at', 'created_by', 'created_at',
                       'audience_preview')
    actions = ['send_campaigns']
    fieldsets = (
        ("E'lon mazmuni", {'fields': ('title', 'text', 'url', 'image')}),
        ('Auditoriya', {'fields': (('gender', 'role'), ('age_min', 'age_max'),
                                   ('neighborhood', 'district'), 'audience_preview')}),
        ('Yuborish', {
            'fields': ('send_to_all', 'target_count', 'status', 'sent_count', 'sent_at'),
            'description': "«Hammaga yuborish» yoqilsa — filtrlarga mos BARCHA foydalanuvchiga "
                           "bir vaqtda yuboriladi (random N ishlatilmaydi). Filtrlar bo'sh "
                           "bo'lsa — butun bazadagi hamma foydalanuvchiga.",
        }),
    )

    @admin.display(description='Yosh')
    def age_range(self, obj):
        if obj.age_min is None and obj.age_max is None:
            return '—'
        return f'{obj.age_min or 0}–{obj.age_max or "∞"}'

    @admin.display(description='Mos auditoriya')
    def audience_preview(self, obj):
        if not obj.pk:
            return '— (avval saqlang)'
        return f'{obj.audience_size()} kishi'

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="🚀 Tanlangan kampaniyalarni yuborish (random N ga)")
    def send_campaigns(self, request, queryset):
        total = 0
        for camp in queryset:
            sent = camp.send()
            total += sent
            self.message_user(
                request, f"«{camp.title}» → {sent} kishiga yuborildi.",
                level=admin_messages.SUCCESS if sent else admin_messages.WARNING)
        if not queryset:
            self.message_user(request, "Hech narsa tanlanmadi.", level=admin_messages.WARNING)


@admin.register(AdCampaignDelivery)
class AdCampaignDeliveryAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'user', 'sent_at')
    list_filter = ('campaign',)
    search_fields = ('user__phone', 'user__name', 'campaign__title')
    readonly_fields = ('campaign', 'user', 'sent_at')


class NeighborhoodAdminForm(forms.ModelForm):
    class Meta:
        model = Neighborhood
        fields = '__all__'
        widgets = {'boundary': PolygonEditorWidget}


class MahallaHokimInline(admin.TabularInline):
    """Mahalla hokimi (raisi) — mahalla qo'shilgan/tahrirlangan payt shu yerda tanlanadi.

    ChatAdmin = mahalla admini: umumiy chatda anonim boshqaradi va shu mahalla
    aholisiga rasmiy e'lon yubora oladi (main.community_views.announcement_create)."""
    model = ChatAdmin
    extra = 1
    autocomplete_fields = ['user']
    verbose_name = 'Mahalla hokimi'
    verbose_name_plural = 'Mahalla hokimlari'


@admin.register(Neighborhood)
class NeighborhoodAdmin(admin.ModelAdmin):
    form = NeighborhoodAdminForm
    inlines = [MahallaHokimInline]
    list_display = ('name', 'district', 'population', 'head_name', 'head_phone', 'color_swatch', 'has_boundary', 'created_at')
    list_filter = ('district',)
    search_fields = ('name', 'head_name', 'head_phone')
    autocomplete_fields = ['district']
    # Markaz (center_lat/center_lng) endi qo'lda kiritilmaydi — xaritada chizilgan
    # poligondan avtomatik hisoblanadi (save_model). Shuning uchun fields'da yo'q.
    fields = ('name', 'district', 'description', 'population', 'head_name', 'head_phone',
              'color', 'boundary')

    def save_model(self, request, obj, form, change):
        # Markazni xaritada belgilangan chegara (poligon) centroididan hisoblab qo'yamiz.
        pts = obj.boundary or []
        if pts:
            obj.center_lat = round(sum(p[0] for p in pts) / len(pts), 6)
            obj.center_lng = round(sum(p[1] for p in pts) / len(pts), 6)
        super().save_model(request, obj, form, change)

    @admin.display(description='Rang')
    def color_swatch(self, obj):
        return mark_safe(
            f'<span style="display:inline-block;width:16px;height:16px;border-radius:4px;'
            f'background:{obj.color or "#ccc"};border:1px solid #999;vertical-align:middle;"></span> '
            f'{obj.color}')

    @admin.display(description='Chegara', boolean=True)
    def has_boundary(self, obj):
        return bool(obj.boundary)


@admin.register(ChatAdmin)
class ChatAdminAdmin(admin.ModelAdmin):
    list_display = ('neighborhood', 'user', 'appointed_at')
    list_filter = ('neighborhood',)
    search_fields = ('user__phone', 'user__name', 'neighborhood__name')
    autocomplete_fields = ['user', 'neighborhood']


# ── MAHALLA: e'lonlar + fuqaro murojaatlari ──────────────────────────────────
@admin.register(NeighborhoodAnnouncement)
class NeighborhoodAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'neighborhood', 'created_by', 'created_at')
    list_filter = ('neighborhood',)
    search_fields = ('title', 'text', 'neighborhood__name')
    readonly_fields = ('created_at',)
    autocomplete_fields = ['neighborhood', 'created_by']

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        # Admin orqali YANGI e'lon ham mahalla aholisiga bildirishnoma bo'lib borsin
        # (web/API yo'llari o'zi yuboradi; bu faqat admin-yaratish uchun).
        if not change:
            from django.urls import reverse
            from .community_views import _notify_mahalla
            sent = _notify_mahalla(
                obj.neighborhood, f"📢 Mahalla e'loni: {obj.title[:60]}",
                reverse('mahalla_detail', args=[obj.neighborhood_id]),
                exclude_user=request.user)
            self.message_user(request, f"{sent} ta aholiga bildirishnoma yuborildi.",
                              level=admin_messages.SUCCESS)


@admin.register(CitizenRequest)
class CitizenRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'neighborhood', 'user', 'status', 'created_at')
    list_filter = ('status', 'category', 'neighborhood')
    search_fields = ('title', 'text', 'user__phone', 'user__name')
    list_editable = ('status',)
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ['neighborhood', 'user', 'responded_by']


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
