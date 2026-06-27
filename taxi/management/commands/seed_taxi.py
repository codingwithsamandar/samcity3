import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from taxi.models import (
    TaxiService, ServiceReview, Taxist, Route, TaxistReview,
    Car, Trip, Payment,
)

User = get_user_model()


DEMO_USERS = [
    ('+998900000001', 'Jasur'), ('+998900000002', 'Dilnoza'),
    ('+998900000003', 'Otabek'), ('+998900000004', 'Malika'),
    ('+998900000005', 'Rustam'), ('+998900000006', 'Gulnora'),
    ('+998900000007', 'Sanjar'), ('+998900000008', 'Nodira'),
]

SERVICES = [
    {'name': 'Shofirkon Taksi', 'short_number': '1265', 'phone': '+998 65 123 12 65',
     'base_price': 5000, 'price_per_km': 2000, 'working_hours': '24/7',
     'description': "Shofirkon shahri va tumani bo'ylab tezkor taksi xizmati."},
    {'name': 'Express Taksi', 'short_number': '1187', 'phone': '+998 65 100 11 87',
     'base_price': 4000, 'price_per_km': 2500, 'working_hours': '06:00–24:00',
     'description': "Arzon va tezkor. Shaharlararo qatnov mavjud."},
    {'name': 'Buxoro Taksi', 'short_number': '1242', 'phone': '+998 65 200 12 42',
     'base_price': 6000, 'price_per_km': 1800, 'working_hours': '24/7',
     'description': "Buxoro viloyati bo'ylab ishonchli xizmat."},
    {'name': 'Tezkor Taksi', 'short_number': '1155', 'phone': '+998 65 300 11 55',
     'base_price': 5000, 'price_per_km': 2200, 'working_hours': '24/7',
     'description': "5 daqiqada mashina. Onlayn buyurtma."},
]

TAXISTS = [
    {'full_name': 'Akmal Karimov', 'phone': '+998 90 111 22 33', 'car_model': 'Chevrolet Nexia 3',
     'trips_count': 1240, 'service': '1265',
     'car': {'brand': 'Chevrolet', 'model': 'Nexia 3', 'color': 'Oq', 'plate_number': '20 A 123 BC',
             'year': 2021, 'seats': 4, 'car_class': 'comfort', 'has_conditioner': True},
     'routes': [('Shofirkon', 'Buxoro', 30000, 15000, "Har kuni 07:00 da jo'naydi"),
                ('Shofirkon', 'Vobkent', 20000, 10000, '')]},
    {'full_name': "Bahodir To'rayev", 'phone': '+998 91 222 33 44', 'car_model': 'Chevrolet Cobalt',
     'trips_count': 860, 'service': '1187',
     'car': {'brand': 'Chevrolet', 'model': 'Cobalt', 'color': 'Kumush', 'plate_number': '20 B 456 CD',
             'year': 2022, 'seats': 4, 'car_class': 'comfort', 'has_conditioner': True, 'has_baby_seat': True},
     'routes': [('Shofirkon', 'Buxoro', 35000, None, 'Konditsioner bor'),
                ('Buxoro', 'Shofirkon', 35000, 18000, '')]},
    {'full_name': 'Sardor Qodirov', 'phone': '+998 93 333 44 55', 'car_model': 'Daewoo Damas',
     'trips_count': 2100, 'service': None,
     'car': {'brand': 'Daewoo', 'model': 'Damas', 'color': 'Oq', 'plate_number': '20 C 789 DE',
             'year': 2019, 'seats': 7, 'car_class': 'minivan', 'allows_pets': True},
     'routes': [('Shofirkon', 'Gijduvon', 25000, 12000, 'Yuk ham olaman'),
                ('Shofirkon', 'Buxoro', 28000, 14000, '')]},
    {'full_name': 'Jamshid Ergashev', 'phone': '+998 94 444 55 66', 'car_model': 'Chevrolet Lacetti',
     'trips_count': 540, 'service': '1242',
     'car': {'brand': 'Chevrolet', 'model': 'Lacetti', 'color': 'Qora', 'plate_number': '20 D 012 EF',
             'year': 2020, 'seats': 4, 'car_class': 'comfort_plus', 'has_conditioner': True},
     'routes': [('Shofirkon', 'Samarqand', 120000, 50000, 'Shaharlararo, oldindan kelishiladi')]},
    {'full_name': "Ulug'bek Nazarov", 'phone': '+998 95 555 66 77', 'car_model': 'Ravon R3',
     'trips_count': 320, 'service': '1155',
     'car': {'brand': 'Ravon', 'model': 'R3', 'color': 'Kulrang', 'plate_number': '20 E 345 FG',
             'year': 2023, 'seats': 4, 'car_class': 'econom', 'has_conditioner': True},
     'routes': [('Shofirkon', 'Buxoro', 32000, 16000, ''),
                ('Shofirkon', 'Romitan', 22000, None, '')]},
]

COMMENTS_POS = [
    "Juda tez keldi, rahmat!", "Mashina toza, haydovchi madaniyatli.",
    "Narxi arzon, tavsiya qilaman.", "Vaqtida yetkazib qo'ydi.",
    "Doim shu xizmatdan foydalanaman.", "Yaxshi xizmat, raqmat.",
    "Ishonchli haydovchi.", "Hammasi joyida bo'ldi.",
]
COMMENTS_NEG = ["Biroz kechikdi.", "Narx biroz qimmat tuyuldi.", "Telefon ko'tarilmadi bir marta."]

CARD_BRANDS = [('8600', 'Uzcard'), ('9860', 'Humo'), ('4', 'Visa')]


class Command(BaseCommand):
    help = "Taksi bo'limi uchun demo ma'lumotlar (xizmatlar, taksistlar, mashinalar, sayohatlar, to'lovlar, baholar)."

    def handle(self, *args, **opts):
        random.seed(42)

        # 1) Demo foydalanuvchilar
        users = []
        for phone, name in DEMO_USERS:
            u, created = User.objects.get_or_create(phone=phone, defaults={'name': name, 'role': 'user'})
            if created:
                u.set_password('demo12345')
                u.save()
            users.append(u)
        self.stdout.write(f"✓ {len(users)} ta demo foydalanuvchi")

        # 2) Taksi xizmatlari + sharhlar
        service_map = {}
        for data in SERVICES:
            svc, _ = TaxiService.objects.update_or_create(
                short_number=data['short_number'],
                defaults={**data, 'region': 'Shofirkon', 'is_active': True},
            )
            service_map[data['short_number']] = svc
            for u in random.sample(users, random.randint(3, 6)):
                rating = random.choices([5, 4, 3], weights=[6, 3, 1])[0]
                ServiceReview.objects.update_or_create(
                    service=svc, user=u,
                    defaults={'rating': rating, 'comment': random.choice(COMMENTS_POS if rating >= 4 else COMMENTS_NEG)},
                )
        self.stdout.write(f"✓ {len(service_map)} ta taksi xizmati + sharhlar")

        # 3) Taksistlar + mashina + marshrutlar + (yakunlangan sayohat + to'lov + baho)
        for data in TAXISTS:
            svc = service_map.get(data['service']) if data['service'] else None
            tx, _ = Taxist.objects.update_or_create(
                full_name=data['full_name'],
                defaults={
                    'phone': data['phone'], 'car_model': data['car_model'],
                    'trips_count': data['trips_count'], 'service': svc,
                    'region': 'Shofirkon', 'is_active': True,
                },
            )

            # Mashina
            Car.objects.update_or_create(taxist=tx, defaults=data['car'])

            # Marshrutlar
            tx.routes.all().delete()
            routes = []
            for a, b, p, d, note in data['routes']:
                routes.append(Route.objects.create(
                    taxist=tx, point_a=a, point_b=b,
                    passenger_price=p, delivery_price=d, note=note, is_active=True,
                ))

            # Yakunlangan sayohatlar + to'lov + baho (faqat sayohat qilganlar baho beradi)
            reviewers = random.sample(users, random.randint(3, 7))
            for u in reviewers:
                route = random.choice(routes)
                trip, _ = Trip.objects.get_or_create(
                    passenger=u, taxist=tx, route=route,
                    defaults={
                        'point_a': route.point_a, 'point_b': route.point_b,
                        'price': route.passenger_price, 'status': 'completed',
                        'payment_method': 'card', 'payment_status': 'paid',
                        'completed_at': timezone.now(),
                    },
                )
                if trip.status != 'completed':
                    trip.status = 'completed'
                    trip.payment_status = 'paid'
                    trip.completed_at = timezone.now()
                    trip.save()

                prefix, brand = random.choice(CARD_BRANDS)
                Payment.objects.update_or_create(
                    trip=trip,
                    defaults={
                        'user': u, 'amount': trip.price, 'card_holder': u.name.upper(),
                        'card_last4': f'{random.randint(0, 9999):04d}', 'card_brand': brand,
                        'status': 'paid', 'paid_at': timezone.now(),
                    },
                )

                rating = random.choices([5, 4, 3], weights=[7, 2, 1])[0]
                TaxistReview.objects.update_or_create(
                    taxist=tx, user=u,
                    defaults={'rating': rating, 'comment': random.choice(COMMENTS_POS if rating >= 4 else COMMENTS_NEG)},
                )
        self.stdout.write(f"✓ {len(TAXISTS)} ta taksist + mashina + sayohatlar + to'lovlar + baholar")

        self.stdout.write(self.style.SUCCESS("\n✅ Demo ma'lumotlar tayyor! Sahifa: /taxi/"))
