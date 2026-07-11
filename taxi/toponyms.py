"""Taxi bo'limidagi manzil/toponim nomlari tarjimasi.

Marshrut punktlari (Route.point_a/point_b) va hudud (region) erkin matn
bo'lgani uchun ma'lum nomlar shu ro'yxat orqali gettext katalogiga kiradi.
Bazaga yangi nom qo'shilsa — shu ro'yxatga ham qo'shib, makemessages/
compilemessages qilish kerak. Notanish nom o'zgarishsiz qaytadi.
"""
from django.utils.translation import gettext_lazy as _

KNOWN_PLACES = [
    _('Buxoro'), _('Buxoro shahri'), _("G'ijduvon"), _('Gijduvon'),
    _('Gazli'), _('Kogon'), _('Markaziy bozor'), _('Romitan'),
    _('Samarqand'), _('Shofirkon'), _('Shofirkon markazi'),
    _("Temir yo'l bekati"), _('Vobkent'), _('Yangibozor'),
]


def localize_place(value):
    from django.utils.translation import gettext
    return gettext(value) if value else value
