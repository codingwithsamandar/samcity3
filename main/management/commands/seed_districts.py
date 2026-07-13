"""Demo tuman (District) + hokim (DistrictAdmin) + aholi biriktirish (idempotent).

    python manage.py seed_districts            # DEBUG=True da
    python manage.py seed_districts --force     # production'da ham

Hokim paneli (/hokim/) ishlashi uchun bazada kamida bitta tuman, unga
bog'langan mahallalar va tayinlangan hokim bo'lishi kerak. Seed shu
ma'lumotni yaratadi: «Shofirkon tumani», unga mavjud mahallalarни biriktiradi,
hokim tayinlaydi va bir necha demo aholi biriktiradi (tuman e'loni kimgadir
borishi uchun). Idempotent: qayta ishga tushirish dublikat yaratmaydi.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from main.models import User, District, DistrictAdmin, Neighborhood

DISTRICT_NAME = 'Shofirkon tumani'
HEAD_NAME = 'Jamshid Xolboyev'
HOKIM_PHONE = '+998900000009'
DEMO_PASSWORD = 'demo12345'

# Tumanga biriktiriladigan mahallalar (mavjud bo'lganlari; chat kanallari emas)
MAHALLA_NAMES = [
    'Shofirkon markaz', 'Guliston', 'Navbahor', 'Yangiobod', "Do'stlik",
    'Bunyodkor', 'Istiqlol', 'Obod', 'Chashma',
]
MIN_RESIDENTS = 12  # tuman e'loni borishi uchun kamida shuncha aholi biriktiriladi


class Command(BaseCommand):
    help = "Demo tuman + hokim + aholi biriktiradi (hokim paneli ishlashi uchun)."

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='DEBUG=False da ham ishga tushiradi (production seed).')

    def handle(self, *args, **opts):
        if not settings.DEBUG and not opts['force']:
            raise CommandError("Bu buyruq faqat DEBUG=True da ishlaydi (--force bilan majburlang).")

        # 1) Tuman
        district, created = District.objects.get_or_create(
            name=DISTRICT_NAME,
            defaults={'head_name': HEAD_NAME, 'head_phone': HOKIM_PHONE,
                      'description': "Shofirkon tumani — mahallalarni birlashtiradi."})
        if not created and not district.head_name:
            district.head_name = HEAD_NAME
            district.head_phone = HOKIM_PHONE
            district.save(update_fields=['head_name', 'head_phone'])
        self.stdout.write(f"Tuman: {district.name} ({'yaratildi' if created else 'mavjud'})")

        # 2) Mahallalarni tumanga biriktiramiz (nomi bo'yicha mavjudlarini)
        linked = 0
        target_mahallas = list(Neighborhood.objects.filter(name__in=MAHALLA_NAMES))
        if not target_mahallas:
            # Zaxira: chat kanali bo'lmagan istalgan mahallalar
            target_mahallas = [
                n for n in Neighborhood.objects.all()
                if not any(k in n.name.lower() for k in ('chat', 'muhokama', 'test', "e'lon"))
            ][:9]
        for nb in target_mahallas:
            if nb.district_id != district.id:
                nb.district = district
                nb.save(update_fields=['district'])
                linked += 1
        self.stdout.write(f"  Biriktirilgan mahallalar: {len(target_mahallas)} ta (yangi: {linked})")

        if not target_mahallas:
            self.stdout.write(self.style.WARNING(
                "  Ogohlantirish: biriktirish uchun mahalla topilmadi — avval seed_mahallas ishlating."))
            return

        # 3) Hokim (DistrictAdmin)
        hokim, huser_created = User.objects.get_or_create(
            phone=HOKIM_PHONE,
            defaults={'name': HEAD_NAME, 'role': 'admin', 'is_active': True})
        if huser_created:
            hokim.set_password(DEMO_PASSWORD)
            hokim.is_active = True
            hokim.save()
        DistrictAdmin.objects.get_or_create(district=district, user=hokim)
        self.stdout.write(
            f"  Hokim: {hokim.phone} ({hokim.name}) "
            f"{'yaratildi' if huser_created else 'mavjud'}, parol={DEMO_PASSWORD}")

        # 4) Aholi biriktirish — tuman e'loni kimgadir borishi uchun
        current = User.objects.filter(neighborhood__district=district, is_active=True).count()
        need = max(0, MIN_RESIDENTS - current)
        assigned = 0
        if need:
            candidates = User.objects.filter(
                role='user', neighborhood__isnull=True, is_active=True
            ).exclude(pk=hokim.pk)[:need]
            for i, u in enumerate(candidates):
                u.neighborhood = target_mahallas[i % len(target_mahallas)]
                u.save(update_fields=['neighborhood'])
                assigned += 1
        total_residents = User.objects.filter(
            neighborhood__district=district, is_active=True).count()
        self.stdout.write(
            f"  Aholi: {total_residents} ta (yangi biriktirilgan: {assigned})")

        self.stdout.write(self.style.SUCCESS(
            f"Tayyor! Hokim paneli: /hokim/ — {hokim.phone} / {DEMO_PASSWORD} bilan kiring."))
