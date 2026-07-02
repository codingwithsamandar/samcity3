"""Admin panelda qayta ishlatiladigan widget'lar.

`LatLngPickerWidget` — kenglik (latitude) maydoniga bog'lanadi va uning ustiga
Leaflet xaritasini chizadi. Xaritada bosilganda `latitude` va `longitude`
maydonlarini (ID orqali topib) avtomatik to'ldiradi — admin endi koordinatani
qo'lda kiritish shart emas.
"""
from django import forms
from django.utils.safestring import mark_safe


class LatLngPickerWidget(forms.NumberInput):
    """`latitude` maydoniga qo'llanadi; `longitude`ni ID orqali (id_longitude) topadi."""

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        attrs.setdefault('id', 'id_%s' % name)
        field_html = super().render(name, value, attrs, renderer)
        return mark_safe(
            '<div class="latlng-picker">'
            '<div id="latlngPickerMap" style="height:320px;border:1px solid #ccc;'
            'border-radius:8px;margin:.4rem 0;"></div>'
            '<p style="font-size:12px;color:#666;margin:.2rem 0 .5rem;">'
            "Joylashuvni xaritada bosib belgilang — kenglik/uzunlik avtomatik to'ldiriladi."
            '</p>' + field_html + '</div>'
        )

    class Media:
        css = {'all': (
            'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css',
        )}
        js = (
            'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js',
            'admin/js/latlng_picker.js',
        )
