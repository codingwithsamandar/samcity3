"""Taxminiy davomiylik — haqiqiy tarixga tayangan.

Nega kerak: `VenueService.duration_minutes` — joy egasi qo'lda kiritgan REJA.
Amalda bir usta soch olishni 20 daqiqada, boshqasi 40 daqiqada bajaradi.
Bu modul yakunlangan bronlardan o'lchov yig'ib, "shu usta shu xizmatni
odatda necha daqiqada bajaradi" degan savolga javob beradi.

Mediana ishlatiladi, o'rtacha emas: bitta unutilgan yozuv (usta "Yakunlandi"
ni ertasiga bosgan) o'rtachani buzadi, medianaga esa deyarli ta'sir qilmaydi.
"""
from statistics import median

# Shuncha o'lchovdan kam bo'lsa — taxminga ishonmaymiz, rejadagi qiymat qoladi.
MIN_SAMPLES = 3
# Faqat oxirgi shuncha yozuv — usta tezlashsa/sekinlashsa taxmin ergashadi.
SAMPLE_LIMIT = 20


def _samples(staff=None, service=None, limit=SAMPLE_LIMIT):
    """Yakunlangan bronlarning haqiqiy davomiyliklari (eng yangisidan)."""
    from .models import VenueBooking

    qs = VenueBooking.objects.filter(
        status='completed', actual_minutes__isnull=False)
    if staff is not None:
        qs = qs.filter(staff=staff)
    if service is not None:
        qs = qs.filter(service=service)
    return list(qs.order_by('-completed_at')
                .values_list('actual_minutes', flat=True)[:limit])


def estimate_minutes(service, staff=None):
    """Xizmatning taxminiy davomiyligi (daqiqa) va uning manbasi.

    Qaytaradi: (daqiqa, manba) — manba 'staff' | 'service' | 'plan'.

    Tartib: avval SHU USTAning shu xizmatdagi tarixi; yetarli bo'lmasa
    xizmatning umumiy tarixi; u ham bo'lmasa rejadagi qiymat.
    """
    plan = getattr(service, 'duration_minutes', None) or 30

    if staff is not None and service is not None:
        rows = _samples(staff=staff, service=service)
        if len(rows) >= MIN_SAMPLES:
            return int(round(median(rows))), 'staff'

    if service is not None:
        rows = _samples(service=service)
        if len(rows) >= MIN_SAMPLES:
            return int(round(median(rows))), 'service'

    return plan, 'plan'


def estimate_label(service, staff=None):
    """Foydalanuvchiga ko'rsatiladigan matn (yoki aniq ma'lumot yo'q bo'lsa None).

    Faqat HAQIQIY o'lchovga tayangan taxmin matn qaytaradi — rejadagi
    qiymatni takrorlab, "taxminan" deb atash foydalanuvchini chalg'itadi.
    """
    mins, source = estimate_minutes(service, staff)
    if source == 'plan':
        return None
    if source == 'staff' and staff is not None:
        return f"{staff.name} buni odatda ~{mins} daqiqada bajaradi"
    return f"Odatda ~{mins} daqiqa davom etadi"
