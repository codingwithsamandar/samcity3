from django import template
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()


@register.filter(name='split')
def split(value, key):
    if value:
        return value.split(key)
    return []


@register.filter(name='uz_price')
def uz_price(value):
    """Narxni mingtayk ajratuvchi bilan formatlaydi: 1 000 000"""
    if value is None or value == '':
        return ''
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return value
    return intcomma(n).replace(',', ' ')
