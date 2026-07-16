"""Markaziy katalogni JSON faylga eksport qiladi (zaxira / ko'chirish uchun).

    python manage.py export_catalog                          # catalog_export.json
    python manage.py export_catalog --output backup.json
    python manage.py export_catalog --include-inactive

Faqat o'qiydi — bazani o'zgartirmaydi.
"""
import json

from django.core.management.base import BaseCommand
from django.utils import timezone

from delivery.models import CatalogProduct


class Command(BaseCommand):
    help = "Markaziy katalogni catalog_export.json ga eksport qiladi."

    def add_arguments(self, parser):
        parser.add_argument('--output', default='catalog_export.json',
                            help='Chiqish fayli (default: catalog_export.json)')
        parser.add_argument('--include-inactive', action='store_true',
                            help='Nofaol (is_active=False) mahsulotlar ham kiritilsin')

    def handle(self, *args, **opts):
        qs = CatalogProduct.objects.select_related('category').order_by('name')
        if not opts['include_inactive']:
            qs = qs.filter(is_active=True)

        items = []
        for c in qs:
            image_path = c.image.name if c.image else None
            try:
                image_url = c.image.url if c.image else None
            except ValueError:
                image_url = None
            items.append({
                'name': c.name,
                'category': c.category.name if c.category else None,
                'brand': c.brand,
                'unit': c.unit,
                'suggested_price': c.suggested_price,
                'description': c.description,
                'image_path': image_path,
                'image_url': image_url,
                'is_active': c.is_active,
            })

        payload = {
            'exported_at': timezone.now().isoformat(),
            'count': len(items),
            'products': items,
        }
        with open(opts['output'], 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        self.stdout.write(self.style.SUCCESS(
            f"{len(items)} ta mahsulot eksport qilindi → {opts['output']}"))
