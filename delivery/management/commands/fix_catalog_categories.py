"""Katalog kategoriya kamchiligini tuzatadi (idempotent).

Import'da 'Household' turi mos kategoriya topmagani uchun 15 ta uy-ro'zg'or
mahsuloti kategoriyasiz (NULL) qolgan edi. Bu buyruq «Uy-ro'zg'or»
kategoriyasini yaratadi va kategoriyasiz katalog mahsulotlarini unga biriktiradi.

    python manage.py fix_catalog_categories

Idempotent: kategoriya bo'lsa qayta yaratmaydi; NULL mahsulot qolmasa hech
narsa qilmaydi. Har deploy'da xavfsiz ishlaydi.
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from delivery.models import CatalogProduct, DeliveryCategory

HOUSEHOLD_NAME = "Uy-ro'zg'or"


class Command(BaseCommand):
    help = "Kategoriyasiz katalog mahsulotlarini «Uy-ro'zg'or» kategoriyasiga biriktiradi."

    def handle(self, *args, **opts):
        cat, created = DeliveryCategory.objects.get_or_create(
            name=HOUSEHOLD_NAME,
            defaults={'slug': slugify('uy-rozgor')},
        )
        self.stdout.write(f"Kategoriya «{HOUSEHOLD_NAME}»: {'yaratildi' if created else 'mavjud'}")

        nulls = CatalogProduct.objects.filter(category__isnull=True)
        n = nulls.count()
        if n:
            updated = nulls.update(category=cat)
            self.stdout.write(self.style.SUCCESS(
                f"Kategoriyasiz {updated} ta mahsulot «{HOUSEHOLD_NAME}»ga biriktirildi."))
        else:
            self.stdout.write("Kategoriyasiz mahsulot yo'q — o'zgarish shart emas.")
