from django.core.management.base import BaseCommand
from payments.models import Provider


PROVIDERS = [
    # Kommunal
    {'name': 'Hududgaz — Shofirkon', 'category': 'kommunal', 'amount': 0, 'phone': '1104',
     'address': 'Shofirkon', 'description': 'Tabiiy gaz uchun to\'lov (abonent kodi bo\'yicha).'},
    {'name': 'Hududiy elektr tarmoqlari', 'category': 'kommunal', 'amount': 0, 'phone': '1142',
     'address': 'Shofirkon', 'description': 'Elektr energiyasi to\'lovi.'},
    {'name': 'Suvoqova — ichimlik suvi', 'category': 'kommunal', 'amount': 0, 'phone': '1116',
     'address': 'Shofirkon', 'description': 'Ichimlik suvi va kanalizatsiya.'},

    # Kurslar
    {'name': 'IT Akademiya — dasturlash kurslari', 'category': 'kurs', 'amount': 450000, 'phone': '+998 90 123 45 67',
     'address': 'Shofirkon markaz', 'description': 'Python, web va mobil dasturlash. Oylik to\'lov.'},
    {'name': 'English Star — til markazi', 'category': 'kurs', 'amount': 300000, 'phone': '+998 90 222 33 44',
     'address': 'Shofirkon', 'description': 'Ingliz tili (IELTS, CEFR). Oylik to\'lov.'},
    {'name': 'Repetitor markazi — matematika/fizika', 'category': 'kurs', 'amount': 250000, 'phone': '+998 91 555 66 77',
     'address': 'Shofirkon', 'description': 'Maktab fanlari bo\'yicha tayyorlov.'},

    # Bog'chalar
    {'name': "1-son bolalar bog'chasi", 'category': 'bogcha', 'amount': 200000, 'phone': '+998 65 700 11 22',
     'address': 'Shofirkon', 'description': 'Oylik to\'lov.'},
    {'name': "Kamalak xususiy bog'cha", 'category': 'bogcha', 'amount': 600000, 'phone': '+998 90 700 33 44',
     'address': 'Shofirkon', 'description': 'To\'liq kunlik xususiy bog\'cha. Oylik.'},

    # Maktablar
    {'name': '5-son umumiy o\'rta maktab', 'category': 'maktab', 'amount': 0, 'phone': '+998 65 710 00 11',
     'address': 'Shofirkon', 'description': 'Maktab jamg\'armasi / qo\'shimcha to\'lovlar.'},
    {'name': 'Bilim xususiy litsey', 'category': 'maktab', 'amount': 800000, 'phone': '+998 90 710 22 33',
     'address': 'Shofirkon', 'description': 'Xususiy litsey o\'qish to\'lovi. Oylik.'},

    # Internet / Aloqa
    {'name': 'UzOnline — internet provayder', 'category': 'internet', 'amount': 110000, 'phone': '+998 71 200 00 00',
     'address': 'Shofirkon', 'description': 'Uy interneti oylik tarif.'},
    {'name': 'Mobil aloqa — balansni to\'ldirish', 'category': 'internet', 'amount': 0, 'phone': '0',
     'address': '—', 'description': 'Telefon raqamiga balans to\'ldirish.'},

    # Boshqa
    {'name': "Mahalla obodonlashtirish jamg'armasi", 'category': 'boshqa', 'amount': 0, 'phone': '—',
     'address': 'Shofirkon', 'description': 'Ixtiyoriy badal / xayriya.'},
]


class Command(BaseCommand):
    help = "To'lovlar bo'limi uchun demo muassasalar yaratadi."

    def handle(self, *args, **opts):
        n = 0
        for data in PROVIDERS:
            Provider.objects.update_or_create(
                name=data['name'],
                defaults={**data, 'region': 'Shofirkon', 'is_active': True},
            )
            n += 1
        self.stdout.write(self.style.SUCCESS(f"✅ {n} ta muassasa tayyor! Sahifa: /payments/"))
