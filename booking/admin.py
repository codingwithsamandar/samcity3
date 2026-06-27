from django.contrib import admin
from .models import Venue, VenueBooking, VenueService, VenueStaff


class VenueServiceInline(admin.TabularInline):
    model = VenueService
    extra = 1


class VenueStaffInline(admin.TabularInline):
    model = VenueStaff
    extra = 1


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('name', 'venue_type', 'owner', 'capacity', 'price_per_day',
                    'cancel_penalty_percent', 'is_active', 'created_at')
    list_filter = ('venue_type', 'is_active')
    search_fields = ('name', 'address', 'owner__phone', 'owner__name')
    list_editable = ('is_active',)
    inlines = [VenueServiceInline, VenueStaffInline]


@admin.register(VenueService)
class VenueServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'venue', 'price', 'duration_minutes', 'is_active')
    list_filter = ('is_active', 'venue__venue_type')
    search_fields = ('name', 'venue__name')


@admin.register(VenueStaff)
class VenueStaffAdmin(admin.ModelAdmin):
    list_display = ('name', 'venue', 'specialty', 'rating', 'reviews_count',
                    'completed_count', 'experience_years', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'venue__name')
    list_editable = ('rating', 'is_active')


@admin.register(VenueBooking)
class VenueBookingAdmin(admin.ModelAdmin):
    list_display = ('venue', 'user', 'booking_date', 'start_time', 'staff', 'service',
                    'status', 'total_amount', 'paid_amount', 'penalty_amount', 'created_at')
    list_filter = ('status', 'venue__venue_type', 'booking_date')
    search_fields = ('venue__name', 'user__phone', 'user__name')
    readonly_fields = ('created_at', 'cancelled_at')
