"""Shablonlar uchun global modul flaglari.

`sdev.settings.TEMPLATES` ichida ro'yxatga olingan. Shablonlarda:

    {% if TAXI_ENABLED %} ... {% endif %}

Flag False bo'lganda `{% url 'taxi:...' %}` HECH QACHON bajarilmasligi kerak —
taksi yo'llari ulanmagani uchun NoReverseMatch beradi.
"""
from django.conf import settings


def feature_flags(request):
    return {
        'TAXI_ENABLED': settings.TAXI_ENABLED,
        'MULTILANG_ENABLED': settings.MULTILANG_ENABLED,
        'DELIVERY_CART_ENABLED': settings.DELIVERY_CART_ENABLED,
        'PAYMENTS_ENABLED': settings.PAYMENTS_ENABLED,
        'HOKIM_ENABLED': settings.HOKIM_ENABLED,
    }


def ad_inquiries(request):
    """E'lonlarga kelgan o'qilmagan savollar soni — navbar/profil badge'i uchun."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {'inquiry_unread': 0}
    from .marketplace_views import unread_inquiry_count
    return {'inquiry_unread': unread_inquiry_count(user)}


def user_personas(request):
    """Rolga moslashgan navigatsiya uchun persona flaglari (main/roles.py).

    Shablonlarda: `{% if is_courier %}`, `{{ courier_new_orders }}` ...
    """
    from .roles import personas
    return personas(request)


def map_tiles(request):
    """Xarita plitka provayderi — shablonlarga (`_map_assets.html`)."""
    return {
        'MAP_TILE_PROVIDER': settings.MAP_TILE_PROVIDER,
        'MAP_TILE_KEY': settings.MAP_TILE_KEY,
    }
