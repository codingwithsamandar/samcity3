from django import template

register = template.Library()


@register.filter(name='stars')
def stars(value):
    """Float/int bahoni yulduzlarga aylantiradi: 4 -> ★★★★☆"""
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        n = 0
    n = max(0, min(5, n))
    return '★' * n + '☆' * (5 - n)


@register.filter(name='som')
def som(value):
    """Sonni ming ajratuvchi bilan formatlaydi: 12000 -> 12 000"""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return value
    return f'{n:,}'.replace(',', ' ')
