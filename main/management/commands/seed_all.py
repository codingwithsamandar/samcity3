from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = ("Barcha demo ma'lumotlarni tayyorlaydi: migratsiyalar, e'lonlar, taksi, "
            "yetkazish, to'lovlar, joylar, mahalla (do'kon/so'rovnoma/xayriya) va "
            "boy investor demo. Production'da ham ishlaydi (mahalla demo'lari force bilan).")

    def handle(self, *args, **opts):
        # (buyruq, izoh, qo'shimcha kwargs)
        steps = [
            ('migrate',        "Migratsiyalar (baza jadvallari)", {}),
            ('demo_data',      "E'lonlar, ish e'lonlari, rezyumelar", {}),
            ('seed_taxi',      "Taksi xizmatlari va taksistlar", {}),
            ('seed_delivery',  "Yetkazib berish do'konlari", {}),
            ('seed_payments',  "To'lov muassasalari", {}),
            ('seed_booking',   "Joylar va bronlar", {}),
            ('seed_places',    "Xarita joylari (barcha toifalar)", {}),
            ('seed_demo_full', "INVESTOR demo — boy realistik ma'lumot (50+ biznes, 300+ mahsulot)", {}),
            # ── Mahalla bo'limi ──
            ('seed_mahallas',    "Mahallalar (xarita chegaralari bilan)", {}),
            ('seed_demo_shops',  "Mahalla do'koni demo (pickup) + hisoblar", {'force': True}),
            ('seed_mahalla_demo', "Mahalla do'kon/joy/so'rovnoma/xayriya demo", {'force': True}),
            ('seed_districts',   "Tuman + hokim + aholi (hokim paneli uchun)", {'force': True}),
        ]
        for cmd, label, kwargs in steps:
            self.stdout.write(self.style.WARNING(f"\n> {label} ..."))
            try:
                call_command(cmd, **kwargs)
            except Exception as e:
                # Bitta bosqich xato bersa ham, qolganini davom ettiramiz.
                self.stdout.write(self.style.ERROR(f"  ! {cmd}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            "\nHammasi tayyor! Sahifalar: / (e'lonlar), /taxi/, /delivery/, "
            "/payments/, /booking/, /jobs/, /mahalla/"
        ))
