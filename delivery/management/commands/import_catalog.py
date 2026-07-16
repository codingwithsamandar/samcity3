"""Markaziy katalogni New/ ma'lumotlaridan import qiladi (Phase 3B).

    python manage.py import_catalog                  # haqiqiy import
    python manage.py import_catalog --dry-run        # simulyatsiya, yozmaydi
    python manage.py import_catalog --validate-only  # TO'LIQ validatsiya (rasm
                                                     # butunligi bilan), yozmaydi

Idempotent: nom bo'yicha (case-insensitive) mavjud yozuv topilsa YANGILAYDI,
dublikat yaratmaydi. Rasm faqat yozuvda rasm bo'lmasa biriktiriladi (qayta
ishga tushirishda fayl takrorlanmaydi). Rasmlar zipdan xotirada o'qilib,
Django storage API orqali saqlanadi — lokal FS ham, Supabase S3 ham ishlaydi.

Tekshiruv hisoboti (catalog_verification_report.md) bo'yicha qarorlar:
  - Birliklar: modeldagi mavjud UNIT_CHOICES qayta ishlatiladi — JSON'dagi
    8 ta begona birlik quyidagi UNIT_MAP bilan mavjudlariga o'tkaziladi.
  - Kategoriyalar: mavjud DeliveryCategory qatorlari qayta ishlatiladi,
    YANGI kategoriya yaratilmaydi. 'Household' mos kelmagani uchun NULL
    bo'lib kiradi (keyin admin orqali biriktiriladi).
  - Rasmi yo'q 28 mahsulot rasmsiz (image=NULL) kiradi.
  - Har bir yozuvda full_clean() chaqiriladi — noto'g'ri qiymat jimgina
    saqlanib qolmasligi uchun; xato bergan qator SKIP qilinadi.
"""
import io
import json
import os
import zipfile

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from delivery.models import CatalogProduct, DeliveryCategory

# JSON'dagi model tanlovidan tashqari birliklar -> mavjud UNIT_CHOICES qiymatlari
UNIT_MAP = {
    'jar': 'piece', 'bar': 'piece', 'can': 'piece', 'roll': 'piece',
    'loaf': 'piece', 'bunch': 'piece', 'tube': 'piece', 'bag': 'pack',
}

# JSON (inglizcha) kategoriya -> mavjud DeliveryCategory nomi. None = NULL.
CATEGORY_MAP = {
    'Beverages': 'Ichimliklar',
    'Dairy & Eggs': 'Oziq-ovqat',
    'Bakery & Grains': 'Non mahsulotlari',
    'Meat & Fish': 'Oziq-ovqat',
    'Fruits & Vegetables': 'Oziq-ovqat',
    'Pantry & Groceries': 'Oziq-ovqat',
    'Snacks & Confectionery': 'Oziq-ovqat',
    'Household': None,  # mos kategoriya yo'q — NULL (admin keyin biriktiradi)
    'Personal Care': "Go'zallik",
}
# Subkategoriya darajasidagi aniqroq moslashuv (kategoriya qoidasidan ustun)
SUBCATEGORY_MAP = {
    ('Personal Care', 'Baby Care'): 'Bolalar',
}


class Command(BaseCommand):
    help = "Markaziy katalogni New/catalog_150_products.json dan import qiladi (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument('--json', default='New/catalog_150_products.json',
                            help='Katalog JSON fayli yo\'li')
        parser.add_argument('--images', default='New/catalog_images.zip',
                            help='Rasmlar zip fayli yo\'li (yo\'q bo\'lsa rasmsiz import)')
        parser.add_argument('--dry-run', action='store_true',
                            help='Hech narsa yozmasdan simulyatsiya qiladi')
        parser.add_argument('--validate-only', action='store_true',
                            help="To'liq validatsiya (dublikatlar, maydon uzunligi, "
                                 "rasm butunligi) — bazaga ham, diskka ham yozmaydi")

    def handle(self, *args, **opts):
        json_path = opts['json']
        if not os.path.exists(json_path):
            raise CommandError(f"JSON topilmadi: {json_path}")
        with open(json_path, encoding='utf-8') as fh:
            data = json.load(fh)
        products = data.get('products') or []
        if not products:
            raise CommandError("JSON'da 'products' bo'sh.")

        zf = None
        if opts['images'] and os.path.exists(opts['images']):
            zf = zipfile.ZipFile(opts['images'])
            zip_names = set(zf.namelist())
        else:
            zip_names = set()
            self.stderr.write(self.style.WARNING(
                f"Rasm zip topilmadi ({opts['images']}) — rasmsiz import qilinadi."))

        validate = opts['validate_only']
        dry = opts['dry_run'] or validate
        cats = {c.name: c for c in DeliveryCategory.objects.all()}
        valid_units = {u for u, _ in CatalogProduct.UNIT_CHOICES}

        created = updated = images_attached = 0
        skipped = []       # (nom, sabab)
        no_image = []      # rasmsiz kirganlar
        no_category = []   # NULL kategoriya bilan kirganlar
        # --validate-only qo'shimcha tekshiruvlari uchun
        seen_names = set()
        json_dups = []     # JSON ichidagi takroriy nomlar
        bad_images = []    # buzuq/katta rasm fayllari
        too_long = []      # maydon uzunligi oshganlar

        for p in products:
            name = (p.get('name') or '').strip()
            if not name:
                skipped.append(('<nomsiz>', "bo'sh nom"))
                continue

            # JSON ichidagi takroriy nomlar (import update_or_create bilan
            # dublikat yaratmaydi, lekin validatsiyada ochiq ko'rsatiladi).
            key = name.casefold()
            if key in seen_names:
                json_dups.append(name)
            seen_names.add(key)
            if validate and (len(name) > 200 or len((p.get('brand') or '').strip()) > 120):
                too_long.append(name)

            # Birlik: mavjud tanlov yoki mapping; ikkalasiga tushmasa — SKIP
            unit = (p.get('unit') or '').strip()
            unit = unit if unit in valid_units else UNIT_MAP.get(unit)
            if unit is None:
                skipped.append((name, f"noma'lum birlik: {p.get('unit')!r}"))
                continue

            # Kategoriya: sub-qoida > kategoriya qoidasi; topilmasa NULL
            cat_key = (p.get('category') or '').strip()
            target_name = SUBCATEGORY_MAP.get(
                (cat_key, (p.get('subcategory') or '').strip()),
                CATEGORY_MAP.get(cat_key))
            if cat_key not in CATEGORY_MAP and (cat_key, (p.get('subcategory') or '').strip()) not in SUBCATEGORY_MAP:
                skipped.append((name, f"noma'lum kategoriya: {cat_key!r}"))
                continue
            category = cats.get(target_name) if target_name else None
            if category is None:
                no_category.append(name)

            fields = {
                'unit': unit,
                'category': category,
                'brand': (p.get('brand') or '').strip()[:120],
                'description': (p.get('description') or '').strip(),
                'is_active': True,
            }
            # Tavsiya narx faqat JSON'da berilgan bo'lsa yoziladi — aks holda
            # qayta import admin panelida qo'lda kiritilgan narxni o'chirib yuborardi.
            if p.get('suggested_price') is not None:
                fields['suggested_price'] = p['suggested_price']

            existing = CatalogProduct.objects.filter(name__iexact=name).first()
            obj = existing or CatalogProduct(name=name)
            for k, v in fields.items():
                setattr(obj, k, v)

            # Rasm: faqat yozuvda rasm YO'Q bo'lsa biriktiriladi (idempotent)
            image_path = p.get('image_path') or ''
            attach = (not obj.image) and image_path in zip_names
            if not obj.image and not attach:
                no_image.append(name)

            # --validate-only: rasm butunligi (haqiqiy WEBP + hajm chegarasi).
            if validate and image_path in zip_names:
                raw = zf.read(image_path)
                if not (raw[:4] == b'RIFF' and raw[8:12] == b'WEBP'):
                    bad_images.append((image_path, "haqiqiy WEBP emas"))
                elif len(raw) > 5 * 1024 * 1024:
                    bad_images.append((image_path, "5MB dan katta"))

            try:
                # Rasm validatorini clean bosqichida ishga tushirmaslik uchun
                # avval matn maydonlari tekshiriladi, rasm keyin biriktiriladi.
                obj.full_clean(exclude=['image', 'created_by', 'promoted_from'])
            except Exception as e:
                skipped.append((name, f'validatsiya xatosi: {e}'))
                continue

            if not dry:
                obj.save()
                if attach:
                    blob = zf.read(image_path)
                    fname = os.path.basename(image_path)
                    obj.image.save(fname, ContentFile(blob), save=True)
            if attach:
                images_attached += 1
            if existing:
                updated += 1
            else:
                created += 1

        mode = ('VALIDATE-ONLY (yozilmadi)' if validate
                else 'DRY-RUN (yozilmadi)' if dry else 'IMPORT')
        v = ('yaratiladi', 'yangilanadi', 'rasm biriktiriladi') if dry \
            else ('yaratildi', 'yangilandi', 'rasm biriktirildi')
        self.stdout.write(self.style.SUCCESS(
            f"[{mode}] {v[0]}: {created}, {v[1]}: {updated}, "
            f"{v[2]}: {images_attached}, skip: {len(skipped)}"))
        self.stdout.write(f"  rasmsiz kirganlar: {len(no_image)}; NULL kategoriya: {len(no_category)}")
        for n, r in skipped:
            self.stdout.write(self.style.WARNING(f"  SKIP: {n} — {r}"))

        if validate:
            # ── To'liq validatsiya xulosasi ──
            def _issue(label, items):
                if items:
                    self.stdout.write(self.style.WARNING(f"  ⚠ {label}: {len(items)}"))
                    for it in items[:10]:
                        self.stdout.write(f"      - {it}")
                else:
                    self.stdout.write(self.style.SUCCESS(f"  ✓ {label}: yo'q"))

            self.stdout.write("")
            self.stdout.write("VALIDATSIYA XULOSASI:")
            _issue("JSON ichidagi takroriy nomlar", json_dups)
            _issue("Buzuq/katta rasm fayllari", [f'{p} — {r}' for p, r in bad_images])
            _issue("Uzunlik oshgan maydonlar (nom>200/brend>120)", too_long)
            problems = skipped or json_dups or bad_images or too_long
            self.stdout.write(
                self.style.WARNING("  Xulosa: muammolar bor — importdan oldin ko'rib chiqing.")
                if problems else
                self.style.SUCCESS("  Xulosa: ma'lumotlar importga TAYYOR ✅"))
