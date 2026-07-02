from django import forms
from django.contrib import admin
from main.admin_widgets import LatLngPickerWidget
from .models import (
    TaxiService, ServiceReview, Taxist, Route, TaxistReview,
    Car, Trip, Payment,
)


class ServiceReviewInline(admin.TabularInline):
    model = ServiceReview
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(TaxiService)
class TaxiServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_number', 'phone', 'base_price', 'price_per_km',
                    'avg_rating', 'review_count', 'region', 'is_active')
    list_filter = ('is_active', 'region')
    search_fields = ('name', 'short_number', 'phone')
    list_editable = ('is_active',)
    inlines = [ServiceReviewInline]


class RouteInline(admin.TabularInline):
    model = Route
    extra = 1


class CarInline(admin.StackedInline):
    model = Car
    extra = 0
    can_delete = True


class TaxistReviewInline(admin.TabularInline):
    model = TaxistReview
    extra = 0
    readonly_fields = ('created_at',)


class TaxistAdminForm(forms.ModelForm):
    class Meta:
        model = Taxist
        fields = '__all__'
        widgets = {'latitude': LatLngPickerWidget}


@admin.register(Taxist)
class TaxistAdmin(admin.ModelAdmin):
    form = TaxistAdminForm
    list_display = ('full_name', 'phone', 'car_model', 'service', 'trips_count',
                    'avg_rating', 'review_count', 'region', 'is_active')
    list_filter = ('is_active', 'region', 'service')
    search_fields = ('full_name', 'phone', 'car_model')
    list_editable = ('is_active', 'trips_count')
    inlines = [CarInline, RouteInline, TaxistReviewInline]


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('taxist', 'point_a', 'point_b', 'passenger_price', 'delivery_price', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('point_a', 'point_b', 'taxist__full_name')


@admin.register(ServiceReview)
class ServiceReviewAdmin(admin.ModelAdmin):
    list_display = ('service', 'user', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('service__name', 'user__phone')


@admin.register(TaxistReview)
class TaxistReviewAdmin(admin.ModelAdmin):
    list_display = ('taxist', 'user', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('taxist__full_name', 'user__phone')


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('taxist', 'brand', 'model', 'color', 'plate_number', 'year', 'car_class', 'seats')
    list_filter = ('car_class', 'has_conditioner')
    search_fields = ('brand', 'model', 'plate_number', 'taxist__full_name')


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('point_a', 'point_b', 'passenger', 'taxist', 'price', 'status', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_status', 'payment_method', 'is_delivery')
    search_fields = ('point_a', 'point_b', 'passenger__phone', 'taxist__full_name')
    readonly_fields = ('created_at', 'completed_at')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('trip', 'user', 'amount', 'card_brand', 'card_last4', 'status', 'paid_at')
    list_filter = ('status', 'card_brand')
    search_fields = ('user__phone', 'card_last4')
    readonly_fields = ('created_at', 'paid_at')
