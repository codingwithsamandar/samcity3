"""Seed (demo ma'lumot) buyruqlari uchun umumiy yordamchilar.

Nega kerak: `Venue.name` da UNIQUE cheklov yo'q — turli seed buyruqlari va
qo'lda kiritilgan joylar tufayli bazada bir xil nomli ikki joy paydo bo'lishi
mumkin. `get_or_create(name=...)` bunday holatda MultipleObjectsReturned bilan
yiqiladi va butun seed to'xtaydi. Shu sababli nom bo'yicha izlashda birinchi
mos yozuv olinadi.
"""


def upsert_venue(defaults=None, update=False, **lookup):
    """Joyni topadi yoki yaratadi — TAKROR nomlarga chidamli.

    lookup   — izlash sharti (odatda name=..., ba'zan owner ham).
    defaults — yaratishda yoziladigan maydonlar.
    update   — True bo'lsa mavjud yozuv ham `defaults` bilan yangilanadi
               (update_or_create o'rnida).

    Qaytaradi: (venue, created) — get_or_create bilan bir xil shakl.
    """
    from .models import Venue

    defaults = defaults or {}
    venue = Venue.objects.filter(**lookup).order_by('created_at').first()
    if venue is None:
        return Venue.objects.create(**lookup, **defaults), True

    if update and defaults:
        for field, value in defaults.items():
            setattr(venue, field, value)
        venue.save()
    return venue, False
