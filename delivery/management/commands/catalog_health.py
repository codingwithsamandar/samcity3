"""Katalog salomatligi hisoboti (faqat o'qiydi, hech narsa o'zgartirmaydi).

    python manage.py catalog_health
"""
from django.core.management.base import BaseCommand

from delivery.catalog_stats import catalog_stats


class Command(BaseCommand):
    help = "Markaziy katalog holati: soni, rasm qamrovi, dublikatlar, nosozliklar."

    def handle(self, *args, **opts):
        s = catalog_stats()
        w = self.stdout.write
        ok = self.style.SUCCESS
        warn = self.style.WARNING

        w("╔══════════════════════════════════════════╗")
        w("║        KATALOG SALOMATLIGI HISOBOTI       ║")
        w("╚══════════════════════════════════════════╝")
        w(f"  Jami mahsulotlar:        {s['total']}")
        w(f"  Faol (is_active=True):   {s['active']}")
        w(f"  Nofaol:                  {s['inactive']}")
        w(f"  Rasmli:                  {s['with_image']}")
        w(f"  Rasmsiz:                 {s['without_image']}")
        w(f"  Rasm qamrovi:            {s['image_coverage_pct']}%")
        w("")

        def issue(label, items, fmt=str):
            if items:
                w(warn(f"  ⚠ {label}: {len(items)}"))
                for it in items[:20]:
                    w(f"      - {fmt(it)}")
                if len(items) > 20:
                    w(f"      ... va yana {len(items) - 20} ta")
            else:
                w(ok(f"  ✓ {label}: yo'q"))

        issue("Takroriy nomlar (katta-kichik harf farqisiz)", s['duplicate_names'])
        issue("Takroriy rasm fayl nomlari", s['duplicate_image_filenames'])
        issue("Noto'g'ri birliklar (UNIT_CHOICES'dan tashqari)", s['invalid_units'])
        if s['null_category']:
            w(warn(f"  ⚠ Kategoriyasiz (NULL) mahsulotlar: {s['null_category']} "
                   f"(admin orqali biriktirish tavsiya etiladi)"))
        else:
            w(ok("  ✓ Kategoriyasiz mahsulotlar: yo'q"))

        w("")
        problems = (bool(s['duplicate_names']) or bool(s['duplicate_image_filenames'])
                    or bool(s['invalid_units']))
        if problems:
            w(warn("  Xulosa: e'tibor talab qiladigan muammolar bor (yuqorida ⚠)."))
        else:
            w(ok("  Xulosa: katalog sog'lom ✅"))
