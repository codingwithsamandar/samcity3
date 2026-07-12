"""Katalog salomatligi ko'rsatkichlari — admin hisoboti va `catalog_health`
buyrug'i uchun YAGONA hisoblash manbai (ikkalasida bir xil raqam chiqishi uchun).

Faqat o'qiydi — hech narsa yozmaydi.
"""
import os
from collections import Counter

from .models import CatalogProduct


def catalog_stats():
    """Katalog bo'yicha barcha ko'rsatkichlarni bitta dict qilib qaytaradi."""
    qs = CatalogProduct.objects.all()
    total = qs.count()
    active = qs.filter(is_active=True).count()
    # Rasm: FileField bo'sh bo'lsa '' saqlanadi (NULL ham bo'lishi mumkin).
    with_image = qs.exclude(image='').exclude(image__isnull=True).count()

    valid_units = {u for u, _ in CatalogProduct.UNIT_CHOICES}
    rows = list(qs.values_list('name', 'unit', 'image', 'category_id'))

    name_counts = Counter(n.strip().casefold() for n, _, _, _ in rows)
    dup_names = sorted(n for n, c in name_counts.items() if c > 1)

    image_basenames = Counter(
        os.path.basename(img) for _, _, img, _ in rows if img)
    dup_images = sorted(b for b, c in image_basenames.items() if c > 1)

    invalid_units = sorted({u for _, u, _, _ in rows if u not in valid_units})
    null_category = sum(1 for _, _, _, cid in rows if cid is None)

    return {
        'total': total,
        'active': active,
        'inactive': total - active,
        'with_image': with_image,
        'without_image': total - with_image,
        'image_coverage_pct': round(with_image * 100 / total, 1) if total else 0.0,
        'duplicate_names': dup_names,
        'duplicate_image_filenames': dup_images,
        'invalid_units': invalid_units,
        'null_category': null_category,
    }


def missing_image_products():
    """Rasmi yo'q katalog mahsulotlari (CSV eksport uchun) — QuerySet."""
    from django.db.models import Q
    return (CatalogProduct.objects
            .filter(Q(image='') | Q(image__isnull=True))
            .select_related('category')
            .order_by('name'))
