from datetime import time, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from booking.models import Venue, VenueBooking, VenueService, VenueStaff

User = get_user_model()

# Shofirkon markazi atrofidagi taxminiy koordinatalar (xaritada ko'rsatish uchun)
COORDS = {
    'toy': (40.1162, 64.5051), 'restoran': (40.1149, 64.5032),
    'barber': (40.1175, 64.5068), 'gym': (40.1133, 64.5009),
    'cafe': (40.1158, 64.5044), 'beauty': (40.1141, 64.5077),
    'zal': (40.1187, 64.5025),
}

# Xizmatlar: key -> [(nom, narx, daqiqa), ...]
SERVICES = {
    'barber': [("Soch olish", 30000, 30), ("Soqol olish", 20000, 20),
               ("Soch + Soqol", 45000, 45), ("Bolalar sochi", 25000, 25)],
    'beauty': [("Manikür", 50000, 40), ("Pedikür", 60000, 50),
               ("Soch turmaklash", 80000, 60), ("Kosmetologiya", 120000, 60)],
    'restoran': [("Oilaviy xona (2 soat)", 50000, 120), ("Banket zali (3 soat)", 200000, 180)],
    'cafe': [("Stol bron (1.5 soat)", 30000, 90)],
}

# Ustalar/ishchilar: key -> [(ism, mutaxassislik), ...]
STAFF = {
    'barber': [("Aziz aka", "Usta sartarosh"), ("Bobur", "Sartarosh"), ("Sardor", "Bolalar ustasi")],
    'beauty': [("Malika", "Kosmetolog"), ("Dilnoza", "Manikür ustasi"), ("Nigora", "Stilist")],
    'restoran': [("Asosiy zal", ""), ("VIP xona", "")],
    'cafe': [("Ofitsiant xizmati", "")],
}


DEMO_USERS = [
    ('+998900000001', 'Jasur'), ('+998900000002', 'Dilnoza'),
    ('+998900000003', 'Otabek'), ('+998900000004', 'Malika'),
    ('+998900000005', 'Rustam'), ('+998900000006', 'Gulnora'),
]

# (key, name, type, desc, address, phone, capacity, price_day, price_hour, wh_start, wh_end)
VENUES = [
    ('toy', 'Shahzoda To\'yxona', 'wedding', "Zamonaviy 350 kishilik zal, sahna va parking bilan.",
     "Shofirkon, Bog' ko'chasi 1", '+998 90 700 10 01', 350, 6000000, None, time(10, 0), time(23, 0)),
    ('restoran', 'Milliy Osh Markazi', 'restaurant', "Milliy taomlar, oilaviy xonalar.",
     "Shofirkon, Markaz", '+998 90 700 20 02', 80, None, 50000, time(9, 0), time(23, 0)),
    ('barber', 'Zamon Barbershop', 'barber', "Erkaklar uchun zamonaviy sartaroshxona.",
     "Shofirkon, Yoshlik ko'chasi 5", '+998 90 700 30 03', None, None, 40000, time(9, 0), time(21, 0)),
    ('gym', 'Olympic Fitness Club', 'gym', "Zamonaviy trenajyorlar, sauna va shaxsiy murabbiy.",
     "Shofirkon, Sport majmuasi", '+998 90 700 40 04', 60, 25000, None, time(6, 0), time(23, 0)),
    ('cafe', 'Cafe Shirin', 'cafe', "Shirinliklar, qahva va yengil taomlar.",
     "Shofirkon, Markaziy maydon", '+998 90 700 50 05', 40, None, 30000, time(8, 0), time(23, 0)),
    ('beauty', 'Malika Beauty Salon', 'beauty', "Soch, manikür, kosmetologiya.",
     "Shofirkon, Gulzor 7", '+998 90 700 60 06', None, None, 60000, time(9, 0), time(20, 0)),
    ('zal', 'Nurafshon Banket Zali', 'other', "Yig'ilish, seminar va tadbirlar uchun universal zal.",
     "Shofirkon, Madaniyat uyi", '+998 90 700 70 07', 120, 900000, None, time(8, 0), time(22, 0)),
]


class Command(BaseCommand):
    help = "Bron bo'limi uchun demo joylar va bronlar yaratadi."

    def handle(self, *args, **opts):
        today = timezone.now().date()

        # Joy egasi
        owner, created = User.objects.get_or_create(
            phone='+998900000010', defaults={'name': 'Demo Biznes', 'role': 'business'},
        )
        if created:
            owner.set_password('demo12345')
            owner.save()

        # Demo foydalanuvchilar
        users = []
        for phone, name in DEMO_USERS:
            u, c = User.objects.get_or_create(phone=phone, defaults={'name': name, 'role': 'user'})
            if c:
                u.set_password('demo12345')
                u.save()
            users.append(u)

        # Joylar
        vmap = {}
        for key, name, vtype, desc, addr, phone, cap, pday, phour, ws, we in VENUES:
            lat, lng = COORDS.get(key, (None, None))
            v, _ = Venue.objects.update_or_create(
                name=name,
                defaults={
                    'owner': owner, 'venue_type': vtype, 'description': desc,
                    'address': addr, 'phone': phone, 'capacity': cap,
                    'price_per_day': pday, 'price_per_hour': phour,
                    'working_hours_start': ws, 'working_hours_end': we, 'is_active': True,
                    'latitude': lat, 'longitude': lng,
                    'cancel_penalty_percent': 10, 'grace_minutes': 15, 'prepay_required': True,
                },
            )
            vmap[key] = v
        self.stdout.write(f"✓ {len(vmap)} ta joy")

        # Xizmatlar va ustalar (sartarosh/salon/restoran/kafe uchun)
        svc_n = staff_n = 0
        for key, items in SERVICES.items():
            v = vmap.get(key)
            if not v:
                continue
            for i, (sname, price, dur) in enumerate(items):
                _, c = VenueService.objects.get_or_create(
                    venue=v, name=sname,
                    defaults={'price': price, 'duration_minutes': dur, 'order': i})
                if c:
                    svc_n += 1
        for key, items in STAFF.items():
            v = vmap.get(key)
            if not v:
                continue
            for i, (sname, spec) in enumerate(items):
                obj, c = VenueStaff.objects.get_or_create(
                    venue=v, name=sname,
                    defaults={
                        'specialty': spec, 'order': i,
                        'rating': round(4.4 + (i % 5) * 0.1, 1),
                        'reviews_count': 20 + i * 17,
                        'completed_count': 90 + i * 60,
                        'experience_years': 3 + (i % 8),
                        'bio': f"{spec or 'Tajribali mutaxassis'} — mijozlar ishonchini qozongan.",
                    })
                # Mavjud ustaga statistika bo'lmasa — qo'shamiz
                if not c and not obj.reviews_count:
                    obj.rating = round(4.4 + (i % 5) * 0.1, 1)
                    obj.reviews_count = 20 + i * 17
                    obj.completed_count = 90 + i * 60
                    obj.experience_years = 3 + (i % 8)
                    obj.bio = obj.bio or f"{spec or 'Tajribali mutaxassis'} — mijozlar ishonchini qozongan."
                    obj.save()
                if c:
                    staff_n += 1
        self.stdout.write(f"✓ {svc_n} ta xizmat, {staff_n} ta usta")

        # Bronlar (turli holatlar va turga mos maydonlar bilan)
        bookings = [
            dict(venue=vmap['toy'], user=users[0], status='pending',
                 booking_date=today + timedelta(days=20), guests=200,
                 event_type='wedding', decoration_needed=True, total_amount=5000000,
                 message="To'y kechki payt, 200 mehmon."),
            dict(venue=vmap['toy'], user=users[2], status='confirmed',
                 booking_date=today + timedelta(days=45), guests=150,
                 event_type='engagement', decoration_needed=False, total_amount=5000000),
            dict(venue=vmap['restoran'], user=users[1], status='confirmed',
                 booking_date=today + timedelta(days=3), start_time=time(19, 0),
                 guests=8, table_count=3, special_request="Tug'ilgan kun, tort uchun joy.",
                 total_amount=150000),
            dict(venue=vmap['barber'], user=users[2], status='confirmed',
                 booking_date=today + timedelta(days=1), start_time=time(15, 0),
                 master_name='Aziz aka', service_type="Soch olish + soqol", total_amount=40000),
            dict(venue=vmap['gym'], user=users[3], status='confirmed',
                 booking_date=today, subscription_type='monthly', total_amount=20000),
            dict(venue=vmap['cafe'], user=users[4], status='pending',
                 booking_date=today + timedelta(days=2), start_time=time(18, 0),
                 guests=4, table_count=2, total_amount=30000),
            dict(venue=vmap['beauty'], user=users[5], status='pending',
                 booking_date=today + timedelta(days=1), start_time=time(11, 0),
                 master_name='Malika', service_type='Manikür + soch', total_amount=60000),
            dict(venue=vmap['zal'], user=users[0], status='completed',
                 booking_date=today - timedelta(days=5), guests=50,
                 message='Mahalla yig\'ilishi.', total_amount=800000),
        ]
        n = 0
        for data in bookings:
            # Takrorlanmaslik uchun: shu user+venue+sana bo'yicha tekshirish
            _, created = VenueBooking.objects.get_or_create(
                venue=data['venue'], user=data['user'], booking_date=data['booking_date'],
                defaults=data,
            )
            if created:
                n += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ {len(vmap)} ta joy, {n} ta bron tayyor! Sahifa: /booking/  (egasi: +998900000010 / demo12345)"
        ))
