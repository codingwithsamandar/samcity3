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
    """Narxni ming ajratuvchi bilan formatlaydi: 1 000 000

    Ajratuvchi HAR DOIM oddiy bo'shliq. `intcomma` faol tilga qarab vergul
    yoki UZILMAS bo'shliq (\\xa0) qaytaradi — natijada bir sahifada narxlar
    ikki xil ko'rinardi (taxi_extras dagi `som` filtri oddiy bo'shliq beradi).
    """
    if value is None or value == '':
        return ''
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return value
    return intcomma(n).replace(',', ' ').replace('\xa0', ' ')
