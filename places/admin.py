from django import forms
from django.contrib import admin
from main.admin_widgets import LatLngPickerWidget
from .models import Place, PlaceImage, PlaceReview, PlaceFavorite


@admin.register(PlaceReview)
class PlaceReviewAdmin(admin.ModelAdmin):
    list_display = ('place', 'user', 'rating', 'created_at')
    list_filter = ('rating',)


admin.site.register(PlaceFavorite)


class PlaceImageInline(admin.TabularInline):
    model = PlaceImage
    extra = 1


class PlaceAdminForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = '__all__'
        widgets = {'latitude': LatLngPickerWidget}


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    form = PlaceAdminForm
    list_display = ('name', 'category', 'address', 'phone', 'is_active', 'created_at')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'address', 'description')
    list_editable = ('is_active',)
    inlines = [PlaceImageInline]


@admin.register(PlaceImage)
class PlaceImageAdmin(admin.ModelAdmin):
    list_display = ('place', 'image')
    search_fields = ('place__name',)
