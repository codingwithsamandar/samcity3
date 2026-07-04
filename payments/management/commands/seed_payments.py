from django.core.management.base import BaseCommand
from payments.models import Provider, CATEGORY_CHOICES


PROVIDERS = [
    # Davlat bog'chalari (faqat ma'lumot — online to'lov yo'q)
    {'name': "1-son bolalar bog'chasi", 'category': 'bogcha_davlat', 'amount': 0, 'phone': '+998 65 700 11 22',
     'address': 'Shofirkon', 'description': 'Davlat bog\'chasi. To\'lov bo\'yicha muassasaga murojaat qiling.'},
    {'name': "12-son bolalar bog'chasi", 'category': 'bogcha_davlat', 'amount': 0, 'phone': '+998 65 700 55 66',
     'address': 'Shofirkon', 'description': 'Davlat bog\'chasi. To\'lov bo\'yicha muassasaga murojaat qiling.'},

    # Shaxsiy bog'chalar
    {'name': "Kamalak shaxsiy bog'cha", 'category': 'bogcha_shaxsiy', 'amount': 600000, 'phone': '+998 90 700 33 44',
     'address': 'Shofirkon', 'description': 'To\'liq kunlik shaxsiy bog\'cha. Oylik to\'lov.'},
    {'name': "Baxtli bolalik shaxsiy bog'cha", 'category': 'bogcha_shaxsiy', 'amount': 550000, 'phone': '+998 90 700 77 88',
     'address': 'Shofirkon', 'description': 'Shaxsiy bog\'cha. Oylik to\'lov.'},

    # Kurslar
    {'name': 'IT Akademiya — dasturlash kurslari', 'category': 'kurs', 'amount': 450000, 'phone': '+998 90 123 45 67',
     'address': 'Shofirkon markaz', 'description': 'Python, web va mobil dasturlash. Oylik to\'lov.'},
    {'name': 'English Star — til markazi', 'category': 'kurs', 'amount': 300000, 'phone': '+998 90 222 33 44',
     'address': 'Shofirkon', 'description': 'Ingliz tili (IELTS, CEFR). Oylik to\'lov.'},
    {'name': 'Repetitor markazi — matematika/fizika', 'category': 'kurs', 'amount': 250000, 'phone': '+998 91 555 66 77',
     'address': 'Shofirkon', 'description': 'Maktab fanlari bo\'yicha tayyorlov.'},

    # Maktablar
    {'name': '5-son umumiy o\'rta maktab', 'category': 'maktab', 'amount': 0, 'phone': '+998 65 710 00 11',
     'address': 'Shofirkon', 'description': 'Maktab jamg\'armasi / qo\'shimcha to\'lovlar.'},
    {'name': 'Bilim xususiy litsey', 'category': 'maktab', 'amount': 800000, 'phone': '+998 90 710 22 33',
     'address': 'Shofirkon', 'description': 'Xususiy litsey o\'qish to\'lovi. Oylik.'},
]


class Command(BaseCommand):
    help = "To'lovlar bo'limi uchun demo muassasalar yaratadi."

    def handle(self, *args, **opts):
        # Endi qo'llab-quvvatlanmaydigan kategoriyalarni (kommunal, internet,
        # boshqa, eski "bogcha") tozalaymiz.
        valid_categories = {key for key, _ in CATEGORY_CHOICES}
        removed = Provider.objects.exclude(category__in=valid_categories).delete()[0]

        n = 0
        for data in PROVIDERS:
            Provider.objects.update_or_create(
                name=data['name'],
                defaults={**data, 'region': 'Shofirkon', 'is_active': True},
            )
            n += 1
        self.stdout.write(self.style.SUCCESS(
            f"{n} ta muassasa tayyor ({removed} ta eski o'chirildi)! Sahifa: /payments/"))
