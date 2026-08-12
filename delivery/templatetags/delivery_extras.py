"""Yetkazib berish uchun shablon yordamchilari."""
from urllib.parse import quote

from django import template

register = template.Library()

# Manzil matni bilan qidirilganda natijani shaharga bog'lash uchun qo'shimcha.
# Aks holda «Guliston MFY, 5-uy» butun O'zbekiston bo'ylab qidiriladi.
CITY_HINT = "Shofirkon, Buxoro viloyati, Oʻzbekiston"


@register.simple_tag
def nav_url(order):
    """Buyurtma manzili uchun tashqi navigator havolasi (Google Maps).

    Koordinata bo'lsa — aniq nuqta; bo'lmasa — manzil matni bo'yicha qidiruv.
    Havola brauzerda ham, telefondagi Maps ilovasida ham ochiladi.
    Manzil ham, koordinata ham bo'lmasa — bo'sh satr (shablon havolani
    umuman chizmaydi).
    """
    lat, lng = order.latitude, order.longitude
    if lat is not None and lng is not None:
        dest = f'{lat},{lng}'
    else:
        addr = (order.address or '').strip()
        if not addr:
            return ''
        dest = f'{addr}, {CITY_HINT}'
    return 'https://www.google.com/maps/dir/?api=1&destination=' + quote(dest)


@register.filter
def has_point(order):
    """Buyurtmada aniq koordinata bormi — ichki xarita shu asosda chiziladi."""
    return order.latitude is not None and order.longitude is not None
