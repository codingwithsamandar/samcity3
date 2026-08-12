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
    }
