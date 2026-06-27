from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = ("Barcha demo ma'lumotlarni tayyorlaydi: avval migratsiyalarni qo'llaydi, "
            "so'ng e'lonlar, taksi, yetkazish va to'lovlar demolarini yaratadi.")

    def handle(self, *args, **opts):
        steps = [
            ('migrate',        "Migratsiyalar (baza jadvallari)"),
            ('demo_data',      "E'lonlar, ish e'lonlari, rezyumelar"),
            ('seed_taxi',      "Taksi xizmatlari va taksistlar"),
            ('seed_delivery',  "Yetkazib berish do'konlari"),
            ('seed_payments',  "To'lov muassasalari"),
            ('seed_booking',   "Joylar va bronlar"),
            ('seed_places',    "Xarita joylari (barcha toifalar)"),
            ('seed_demo_full', "INVESTOR demo — boy realistik ma'lumot (50+ biznes, 300+ mahsulot)"),
        ]
        for cmd, label in steps:
            self.stdout.write(self.style.WARNING(f"\n▶ {label} ..."))
            call_command(cmd)

        self.stdout.write(self.style.SUCCESS(
            "\n✅ Hammasi tayyor! Sahifalar: / (e'lonlar), /taxi/, /delivery/, /payments/, /booking/, /jobs/"
        ))
