"""
Shofirkon Super App — INVESTOR DEMO uchun boy, realistik ma'lumot.

Mavjud seedlar (demo_data, seed_taxi, seed_delivery, ...) USTIGA qo'shiladi.
Additive va idempotent: bir necha marta ishlatish xavfsiz (get_or_create / update_or_create).

Ishlatish:
    python manage.py seed_demo_full
    python manage.py seed_demo_full --clear   (avval shu buyruq yaratgan demo'ni tozalaydi)

Yaratadi (taxminan):
    ~32 fuqaro + ~16 biznes egasi foydalanuvchi
    ~60 xarita joyi (restoran, dorixona, shifoxona, mehmonxona, to'yxona, bank, ta'lim, ...)
    ~55 do'kon + 350+ mahsulot (delivery)
    ~22 taksist + mashina + AB marshrutlar + xizmatlar
    ~16 venue (to'yxona/restoran/salon/sport)
    ~22 to'lov muassasasi (payments)
    ~24 marketplace e'loni
    yuzlab sharh/baho (rating ko'rinishi uchun)
"""
import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify

User = get_user_model()

# Shofirkon tumani (Buxoro viloyati) markazi
BASE_LAT, BASE_LNG = 40.1180, 64.5010

RNG = random.Random(2025)  # reproducible


def coord():
    return (round(BASE_LAT + RNG.uniform(-0.025, 0.025), 6),
            round(BASE_LNG + RNG.uniform(-0.03, 0.03), 6))


# ─────────────────────────────────────────────────────────────────────────────
# FOYDALANUVCHILAR (deterministik telefon raqamlar — mavjudlar bilan to'qnashmaydi)
# ─────────────────────────────────────────────────────────────────────────────
CITIZEN_NAMES = [
    "Akmal Rahimov", "Dilfuza Karimova", "Shoxrux Tursunov", "Gulnora Sobirova",
    "Bekzod Yusupov", "Madina Ergasheva", "Sardor Qodirov", "Nigora Tosheva",
    "Javohir Aliyev", "Sevara Mirzayeva", "Otabek Nazarov", "Kamola Saidova",
    "Rustam Bobomurodov", "Zarina Hamroyeva", "Aziz Sharipov", "Feruza Umarova",
    "Doston Egamberdiyev", "Mohira Yo'ldosheva", "Ulug'bek To'rayev", "Dilnoza Rasulova",
    "Sanjar Ismoilov", "Laylo Abdullayeva", "Jahongir Qosimov", "Nilufar Berdiyeva",
    "Temur Xolmatov", "Shahnoza Olimova", "Farrux Sodiqov", "Malika Toirova",
    "Islom Yoqubov", "Gavhar Nurmatova", "Bahodir Eshonqulov", "Ziyoda Hakimova",
]
OWNER_NAMES = [
    "Anvar Soliyev", "Dildora Ahmedova", "Shavkat Murodov", "Gulchehra Po'latova",
    "Eldor To'xtayev", "Nasiba Qurbonova", "Komil Razzoqov", "Oysha Yorqulova",
    "Mirjalol Usmonov", "Dilrabo Kamolova", "Asror Hayitov", "Sojida Maxmudova",
    "Behruz Salimov", "Munira Ochilova", "Qahramon Davlatov", "Ra'no Toshpo'latova",
]


class Command(BaseCommand):
    help = "Investor demo uchun boy, realistik Shofirkon ma'lumotlarini yuklaydi."

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true',
                            help="Shu buyruq yaratgan demo ma'lumotlarni o'chiradi")

    # ── helperlar ────────────────────────────────────────────────────────────
    def _user(self, phone, name, role='user'):
        u, created = User.objects.get_or_create(
            phone=phone, defaults={'name': name, 'role': role})
        if created:
            u.set_password('demo1234')
            u.save()
        return u

    def handle(self, *args, **opts):
        if opts['clear']:
            self._clear()
            return

        self.stdout.write("=" * 60)
        self.stdout.write("🚀 Shofirkon investor-demo ma'lumotlari yuklanmoqda...")
        self.stdout.write("=" * 60)

        citizens = [self._user(f'+99893{i:07d}', n, 'user')
                    for i, n in enumerate(CITIZEN_NAMES, start=1)]
        owners = [self._user(f'+99895{i:07d}', n, 'business')
                  for i, n in enumerate(OWNER_NAMES, start=1)]
        self.stdout.write(f"👤 Foydalanuvchilar: {len(citizens)} fuqaro + {len(owners)} biznes egasi")

        self._seed_places(citizens)
        self._seed_delivery(owners, citizens)
        self._seed_taxi(citizens)
        self._seed_venues(owners, citizens)
        self._seed_providers()
        self._seed_ads(citizens)
        # ── Avval demo'siz qolgan funksiyalar ──
        self._seed_community(citizens)
        self._seed_taxi_trips(citizens)
        self._seed_delivery_drivers(citizens)
        self._seed_service_payments(citizens)
        self._seed_engagement(citizens)

        self._report()

    # ── 1. XARITA JOYLARI (zich — investor demo, ~210 joy) ─────────────────────
    def _seed_places(self, citizens):
        from places.models import Place, PlaceReview

        AREAS = ["Markaz", "Navoiy", "Mustaqillik", "Bog'", "Yangiobod", "Gulshan",
                 "Do'stlik", "Bahor", "Chorbog'", "Guliston", "Hamkor", "Obod",
                 "Istiqlol", "Fayzobod"]
        # category -> (base nomlar, nechta, ish vaqti)
        PLAN = {
            'restaurant': (["Milliy Taomlar", "Osh Markazi", "Choyxona", "Tandir",
                            "Kabobxona", "Pizza House", "Fast Food", "Anor Restoran",
                            "Registon Restoran", "Saodat Taomxona"], 32, "09:00-23:00"),
            'pharmacy': (["Dori-Darmon", "Salomatlik Apteka", "Shifo Dorixona",
                          "OxyMed", "Nur Apteka", "Tungi Dorixona"], 22, "08:00-22:00"),
            'hospital': (["Oila Poliklinikasi", "Sihat Klinikasi", "Stomatologiya",
                          "Diagnostika Markazi", "Bolalar Shifoxonasi", "Ginekologiya",
                          "Laboratoriya"], 16, "24/7"),
            'hotel': (["Grand Hotel", "Palace Hotel", "Karvon Saroy", "Oasis Hotel",
                       "Buxoro Inn"], 9, "24/7"),
            'wedding': (["Sharqona To'yxona", "Navro'z To'yxona", "Registon To'yxona",
                         "Guliston To'yxona", "Oltin Saroy"], 13, "10:00-24:00"),
            'bank': (["Milliy Bank", "Ipoteka Bank", "Xalq Banki", "Agrobank",
                      "Kapitalbank", "Mikrokreditbank"], 11, "09:00-17:00"),
            'government': (["Davlat Xizmatlari Markazi", "Soliq Inspeksiyasi",
                            "Bandlik Markazi", "Fuqarolar Yig'ini", "Statistika Boshqarmasi"], 9, "09:00-18:00"),
            'post': (["Pochta Bo'limi", "EMS Express"], 6, "09:00-18:00"),
            'electronics': (["Texnomart", "Mobil Dunyo", "Elektron Plaza",
                             "Smart Shop", "Texno Bozor"], 16, "09:00-21:00"),
            'furniture': (["Mebel Saroyi", "Uy Komfort", "Klassik Mebel",
                           "Soft Mebel"], 12, "09:00-20:00"),
            'tourist': (["Tarixiy Maydon", "Eski Karvonsaroy", "Bog' Park",
                         "Madaniyat Markazi", "Yodgorlik"], 10, "24/7"),
            'organization': (["O'quv Markazi", "Til Markazi", "IT Akademiya",
                              "Repetitorlik Markazi", "Sartaroshxona", "Avto Servis",
                              "Fermer Xo'jaligi", "Go'zallik Saloni", "Bolalar Bog'chasi"], 32, "09:00-19:00"),
            'delivery_store': (["Market", "Supermarket", "Mahalla Do'koni",
                                "Oziq-ovqat Do'koni", "Mini Market"], 22, "08:00-23:00"),
        }
        DESC = {
            'restaurant': "Milliy va Yevropa taomlari, oilaviy zal, yetkazib berish.",
            'pharmacy': "Sertifikatlangan dori-darmon va tibbiy vositalar.",
            'hospital': "Malakali shifokorlar, zamonaviy diagnostika va davolash.",
            'hotel': "Qulay xonalar, nonushta, konditsioner va Wi-Fi.",
            'wedding': "Katta zal, sahna, bezatish va ovqatlanish xizmati.",
            'bank': "Omonatlar, plastik kartalar, kreditlar va onlayn xizmatlar.",
            'government': "Fuqarolarga davlat xizmatlari — tez va shaffof.",
            'post': "Pochta jo'natmalari, EMS va kommunal to'lovlar.",
            'electronics': "Telefon, maishiy texnika va aksessuarlar — kafolat bilan.",
            'furniture': "Uy va ofis mebellari, buyurtma asosida tayyorlash.",
            'tourist': "Shofirkonning diqqatga sazovor joyi — sayohatchilar uchun.",
            'organization': "Zamonaviy xizmat ko'rsatuvchi tashkilot.",
            'delivery_store': "Oziq-ovqat va kundalik mahsulotlar, yetkazib berish.",
        }
        review_texts = [
            "Juda zo'r xizmat, tavsiya qilaman!", "Tez va sifatli, rahmat.",
            "Narxlari hamyonbop, xodimlar xushmuomala.", "Toza va qulay joy.",
            "Yana kelaman, hammasi a'lo darajada.", "Kutganimdan ham yaxshi chiqdi.",
        ]

        n_place = n_rev = 0
        for category, (bases, count, hours) in PLAN.items():
            seen = {}
            for i in range(count):
                base = bases[i % len(bases)]
                area = AREAS[i % len(AREAS)]
                k = (base, area)
                seen[k] = seen.get(k, 0) + 1
                # Deterministik, takrorlanmas nom (idempotent)
                name = base + " — " + area + ((" " + str(seen[k])) if seen[k] > 1 else "")
                lat = round(BASE_LAT + RNG.uniform(-0.045, 0.045), 6)
                lng = round(BASE_LNG + RNG.uniform(-0.05, 0.05), 6)
                place, created = Place.objects.get_or_create(
                    name=name, category=category,
                    defaults={
                        'description': DESC.get(category, "Shofirkon hududidagi muassasa."),
                        'latitude': lat, 'longitude': lng,
                        'address': "Shofirkon tumani, " + area + " mahallasi, " + str(RNG.randint(1, 120)) + "-uy",
                        'phone': "+998 65 " + str(RNG.randint(200, 599)) + "-" + str(RNG.randint(10, 99)) + "-" + str(RNG.randint(10, 99)),
                        'working_hours': hours,
                        'is_active': True,
                        'views': RNG.randint(120, 8600),
                    })
                n_place += 1
                if created and RNG.random() < 0.45:
                    for u in RNG.sample(citizens, RNG.randint(2, 5)):
                        _, c = PlaceReview.objects.get_or_create(
                            place=place, user=u,
                            defaults={'rating': RNG.randint(3, 5),
                                      'text': RNG.choice(review_texts)})
                        if c:
                            n_rev += 1
        self.stdout.write("📍 Xarita joylari: " + str(n_place) + " ta (+" + str(n_rev) + " sharh)")

    # ── 2. DELIVERY: do'kon + mahsulot ─────────────────────────────────────────
    def _seed_delivery(self, owners, citizens):
        from delivery.models import DeliveryCategory, Store, Product

        # category -> (do'kon bazaviy nomi, mahsulot pool [(nom, narx_min, narx_max)])
        CAT = {
            'Oziq-ovqat': ("Market", [
                ("Guruch Lazer 1kg", 16000, 22000), ("Yog' Oltin 1L", 20000, 26000),
                ("Shakar 1kg", 11000, 14000), ("Tuxum 10 dona", 14000, 19000),
                ("Un Oliy nav 1kg", 7000, 10000), ("Makaron 400g", 6000, 9000),
                ("Choy Akbar 250g", 18000, 26000), ("Tuz 1kg", 2500, 4000),
                ("Konserva baliq", 15000, 22000), ("Pishloq 200g", 22000, 32000)]),
            'Restoran': ("Taomlar", [
                ("Osh 1 porsiya", 26000, 34000), ("Manti 5 dona", 22000, 30000),
                ("Lag'mon", 24000, 32000), ("Somsa 1 dona", 5000, 8000),
                ("Shashlik 1 six", 18000, 26000), ("Norin", 28000, 36000),
                ("Mastava", 18000, 24000), ("Salat Achichuk", 9000, 14000)]),
            'Dorixona': ("Apteka", [
                ("Parasetamol", 7000, 11000), ("Vitamin C", 20000, 30000),
                ("Niqob 50 dona", 25000, 38000), ("Bint steril", 6000, 10000),
                ("Antiseptik 100ml", 12000, 18000), ("Termometr", 35000, 60000),
                ("Yo'tal siropi", 22000, 34000), ("Bosim o'lchagich", 180000, 320000)]),
            'Non mahsulotlari': ("Tandir", [
                ("Tandir non", 3500, 5000), ("Patir", 7000, 10000),
                ("Kulcha 5 dona", 12000, 18000), ("Lochira", 9000, 14000),
                ("Shirmoy non", 6000, 9000)]),
            'Ichimliklar': ("Drinks", [
                ("Coca-Cola 1L", 11000, 14000), ("Suv 1.5L", 3500, 5000),
                ("Sok 1L", 13000, 18000), ("Fanta 1L", 11000, 14000),
                ("Energetik 0.5L", 14000, 20000), ("Choy sovuq 1L", 9000, 13000)]),
            'Gullar': ("Gulzor", [
                ("Atirgul 1 dona", 10000, 16000), ("Buket Sevgi", 150000, 250000),
                ("Buket 11 atirgul", 120000, 180000), ("Tюльpan 1 dona", 12000, 18000),
                ("Bayram buketi", 90000, 160000)]),
            'Elektronika': ("Texno", [
                ("Quloqchin TWS", 120000, 280000), ("Powerbank 10000mAh", 90000, 160000),
                ("USB-C kabel", 18000, 35000), ("Telefon g'ilofi", 25000, 60000),
                ("Smart soat", 250000, 650000), ("Bluetooth kolonka", 180000, 420000)]),
            "Go'zallik": ("Beauty", [
                ("Shampun 400ml", 28000, 45000), ("Krem yuz uchun", 35000, 70000),
                ("Atir 50ml", 120000, 280000), ("Sochrang", 22000, 38000),
                ("Maska to'plami", 30000, 55000)]),
            'Bolalar': ("Bolajon", [
                ("Pampers 40 dona", 75000, 110000), ("Bolalar shampuni", 25000, 40000),
                ("O'yinchoq mashina", 35000, 80000), ("Konstruktor", 60000, 140000),
                ("Bolalar kitobi", 18000, 35000)]),
            'Sport': ("Sport", [
                ("Gantel 5kg juft", 90000, 160000), ("Yoga gilam", 70000, 130000),
                ("Sport futbolka", 60000, 120000), ("Skakalka", 18000, 35000),
                ("Suv idishi 1L", 25000, 45000)]),
            'Kiyim': ("Moda", [
                ("Ko'ylak erkaklar", 90000, 180000), ("Jinsi shim", 120000, 220000),
                ("Ayollar libosi", 150000, 350000), ("Krossovka", 180000, 420000),
                ("Bolalar to'plami", 70000, 140000)]),
            'Qurilish': ("Stroy", [
                ("Sement 50kg", 38000, 52000), ("Bo'yoq oq 5L", 75000, 120000),
                ("G'isht 100 dona", 90000, 140000), ("Plitka 1m²", 55000, 95000),
                ("Elektr kabel 10m", 35000, 60000)]),
        }
        # nechta do'kon (kategoriya bo'yicha)
        COUNTS = {'Oziq-ovqat': 8, 'Restoran': 8, 'Dorixona': 6, 'Non mahsulotlari': 4,
                  'Ichimliklar': 4, 'Gullar': 3, 'Elektronika': 5, "Go'zallik": 4,
                  'Bolalar': 3, 'Sport': 3, 'Kiyim': 4, 'Qurilish': 3}
        PREFIX = ["Mega", "Oila", "Bahor", "Registon", "Chinor", "Sharq", "Yangi",
                  "Nur", "Baraka", "Diyor", "Hilol", "Saodat", "Zilol", "Marvarid"]

        cat_map = {}
        for name in CAT:
            cat, _ = DeliveryCategory.objects.get_or_create(
                slug=slugify(name) or name.lower(), defaults={'name': name})
            cat_map[name] = cat

        n_store = n_prod = 0
        for cat_name, (base, pool) in CAT.items():
            for i in range(COUNTS[cat_name]):
                store_name = f"{PREFIX[i % len(PREFIX)]} {base}"
                if Store.objects.filter(name=store_name).exists():
                    store_name = f"{PREFIX[i % len(PREFIX)]} {base} #{i+1}"
                lat, lng = coord()
                store, _ = Store.objects.update_or_create(
                    name=store_name,
                    defaults={
                        'owner': RNG.choice(owners),
                        'category': cat_map[cat_name],
                        'description': f"{cat_name} — Shofirkon bo'ylab tez yetkazib berish.",
                        'address': f"Shofirkon, {RNG.choice(['Markaziy', 'Bog', 'Bozor', 'Navoiy'])} ko'chasi {RNG.randint(1, 60)}",
                        'latitude': lat, 'longitude': lng,
                        'phone': f"+998 90 {RNG.randint(100, 999)}-{RNG.randint(10, 99)}-{RNG.randint(10, 99)}",
                        'is_active': True,
                    })
                n_store += 1
                for (pname, pmin, pmax) in RNG.sample(pool, min(len(pool), RNG.randint(6, 8))):
                    price = RNG.randrange(pmin, pmax + 1, 500)
                    Product.objects.update_or_create(
                        store=store, name=pname,
                        defaults={'price': price, 'stock': RNG.randint(8, 200),
                                  'is_available': True})
                    n_prod += 1
        self.stdout.write(f"🛒 Do'konlar: {n_store} ta, mahsulotlar: {n_prod} ta")

    # ── 3. TAKSI: taksist + mashina + marshrut + xizmat + sharh ─────────────────
    def _seed_taxi(self, citizens):
        from taxi.models import TaxiService, Taxist, Car, Route, TaxistReview, ServiceReview

        services = [
            ("Shofirkon Taxi 1265", "1265", 8000, 2500),
            ("Express Yo'l 1187", "1187", 10000, 2800),
            ("Buxoro Trans", "1133", 9000, 2600),
        ]
        svc_objs = []
        for name, num, base, perkm in services:
            s, _ = TaxiService.objects.get_or_create(
                name=name,
                defaults={'short_number': num, 'phone': f'+998 65 223-{RNG.randint(10,99)}-{RNG.randint(10,99)}',
                          'description': "Shahar va tumanlararo qulay taksi xizmati.",
                          'base_price': base, 'price_per_km': perkm,
                          'working_hours': '24/7', 'region': 'Shofirkon', 'is_active': True})
            svc_objs.append(s)
            for u in RNG.sample(citizens, RNG.randint(3, 6)):
                ServiceReview.objects.get_or_create(
                    service=s, user=u,
                    defaults={'rating': RNG.randint(4, 5), 'comment': "Tez yetib keldi, rahmat."})

        DRIVERS = [
            "Olim Karimov", "Sherzod Ahmedov", "Bahrom Yo'ldoshev", "Qudrat Nazarov",
            "Ravshan Sobirov", "Ilhom Tursunov", "Akbar Rasulov", "Davron Qosimov",
            "Murod Eshonov", "Sanjar Hakimov", "Botir Olimov", "G'ayrat Sodiqov",
            "Zafar Umarov", "Nodir Bekov", "Shuhrat Aliyev", "Jamshid Yusupov",
            "Anvar To'rayev", "Kamol Sharipov", "Eldor Mirzayev", "Dilshod Qodirov",
            "Ozod Hamroyev", "Farhod Berdiyev",
        ]
        CARS = [("Chevrolet", "Cobalt"), ("Chevrolet", "Nexia 3"), ("Chevrolet", "Spark"),
                ("Chevrolet", "Lacetti"), ("Chevrolet", "Malibu"), ("Daewoo", "Matiz"),
                ("Kia", "K5"), ("Hyundai", "Sonata"), ("Chevrolet", "Onix")]
        COLORS = ["Oq", "Qora", "Kumush", "Kulrang", "Ko'k"]
        POINTS = ["Shofirkon markazi", "Buxoro shahri", "Vobkent", "Gazli", "G'ijduvon",
                  "Kogon", "Yangibozor", "Temir yo'l bekati", "Markaziy bozor"]

        n_tx = n_route = 0
        for i, nm in enumerate(DRIVERS, start=1):
            u = self._user(f'+99897{i:07d}', nm, 'driver')
            online = RNG.random() < 0.55
            lat, lng = coord()
            tx, created = Taxist.objects.get_or_create(
                full_name=nm, phone=u.phone,
                defaults={
                    'user': u, 'service': RNG.choice(svc_objs),
                    'car_model': "—", 'region': 'Shofirkon',
                    'trips_count': RNG.randint(40, 2200),
                    'is_active': True, 'is_online': online,
                    'latitude': lat if online else None,
                    'longitude': lng if online else None,
                    'location_updated_at': timezone.now() if online else None,
                })
            n_tx += 1
            brand, model = RNG.choice(CARS)
            Car.objects.get_or_create(
                taxist=tx,
                defaults={'brand': brand, 'model': model, 'color': RNG.choice(COLORS),
                          'plate_number': f"{RNG.randint(10,99)} {RNG.choice('ABCDEFGHK')}{RNG.randint(100,999)}{RNG.choice('ABCDEFGHK')}{RNG.choice('ABCDEFGHK')}",
                          'year': RNG.randint(2015, 2024), 'seats': 4,
                          'car_class': RNG.choice(['econom', 'econom', 'comfort', 'comfort_plus']),
                          'has_conditioner': RNG.random() < 0.8,
                          'has_baby_seat': RNG.random() < 0.3,
                          'allows_pets': RNG.random() < 0.2})
            # 1–3 marshrut
            a = "Shofirkon markazi"
            used = set()
            for _ in range(RNG.randint(1, 3)):
                b = RNG.choice([p for p in POINTS if p != a])
                if b in used:
                    continue
                used.add(b)
                pp = RNG.randrange(8000, 60000, 1000)
                Route.objects.get_or_create(
                    taxist=tx, point_a=a, point_b=b,
                    defaults={'passenger_price': pp,
                              'delivery_price': pp + RNG.randrange(5000, 20000, 1000),
                              'note': RNG.choice(["Konditsioner bor", "4 kishi", "Pochta ham", ""]),
                              'is_active': True})
                n_route += 1
            # sharhlar
            for cu in RNG.sample(citizens, RNG.randint(2, 5)):
                TaxistReview.objects.get_or_create(
                    taxist=tx, user=cu,
                    defaults={'rating': RNG.randint(4, 5), 'comment': "Yaxshi haydovchi."})
        self.stdout.write(f"🚖 Taksistlar: {n_tx} ta (+{n_route} marshrut, {len(svc_objs)} xizmat)")

    # ── 4. VENUE (booking) ─────────────────────────────────────────────────────
    def _seed_venues(self, owners, citizens):
        from booking.models import Venue, VenueBooking, VenueService, VenueStaff
        from datetime import time as _t

        # Joy turiga qarab namuna xizmatlar va ustalar (slot turlari uchun)
        SVC_TPL = {
            'barber': [("Soch olish", 30000, 30), ("Soqol olish", 20000, 20),
                       ("Soch + Soqol", 45000, 45), ("Bolalar sochi", 25000, 25)],
            'beauty': [("Manikür", 50000, 40), ("Pedikür", 60000, 50),
                       ("Soch turmaklash", 80000, 60), ("Makiyaj", 100000, 60)],
            'restaurant': [("Oilaviy xona (2 soat)", 50000, 120),
                           ("Banket zali (3 soat)", 200000, 180)],
            'cafe': [("Stol bron (1.5 soat)", 30000, 90)],
        }
        STAFF_TPL = {
            'barber': [("Aziz usta", "Usta sartarosh"), ("Bobur", "Sartarosh"), ("Sardor", "Bolalar ustasi")],
            'beauty': [("Malika", "Kosmetolog"), ("Dilnoza", "Manikür ustasi"), ("Nigora", "Stilist")],
            'restaurant': [("Asosiy zal", ""), ("VIP xona", "")],
            'cafe': [("Ofitsiant xizmati", "")],
        }

        DATA = [
            ('wedding', "Sharqona To'yxona", 500, 12000000, "To'liq bezatish va oshxona bilan."),
            ('wedding', "Navro'z To'yxona", 350, 9000000, "Sahna, yorug'lik, professional ovqat."),
            ('wedding', "Oltin Saroy", 700, 18000000, "VIP zal, 700 kishilik."),
            ('restaurant', "Registon Restorani", 120, None, "Milliy va Yevropa taomlari."),
            ('restaurant', "Chinor Choyxona", 80, None, "Oilaviy zal, tandir taomlar."),
            ('cafe', "Bahor Kafe", 40, None, "Qahva, shirinliklar, Wi-Fi."),
            ('cafe', "Coffee Time", 30, None, "Zamonaviy kofexona markazda."),
            ('barber', "Barber House", 6, None, "Erkaklar sartaroshxonasi, usta xizmati."),
            ('barber', "Style Barber", 5, None, "Soch va soqol, zamonaviy uslub."),
            ('beauty', "Malika Go'zallik Saloni", 8, None, "Soch, tirnoq, makiyaj."),
            ('beauty', "Venera Salon", 6, None, "To'y bezagi va parvarish."),
            ('gym', "Power Gym", 60, 250000, "Zamonaviy trenajyorlar, murabbiy."),
            ('gym', "Fit Zone", 45, 200000, "Fitnes va guruh mashg'ulotlari."),
            ('restaurant', "Anor Restorani", 150, None, "Banket va tantanalar uchun."),
            ('wedding', "Guliston To'yxona", 400, 10000000, "Bog'li hovli, fontan."),
            ('beauty', "Glamour Studio", 7, None, "Make-up va stilistika."),
        ]
        EVENTS = ['wedding', 'birthday', 'engagement', 'other']
        n_v = n_b = 0
        for i, (vtype, name, cap, ppd, desc) in enumerate(DATA):
            _lat = round(40.110 + RNG.random() * 0.013, 6)
            _lng = round(64.498 + RNG.random() * 0.013, 6)
            v, _ = Venue.objects.get_or_create(
                name=name,
                defaults={
                    'owner': owners[i % len(owners)], 'venue_type': vtype,
                    'description': desc, 'address': f"Shofirkon, Markaziy ko'cha {RNG.randint(1, 50)}",
                    'phone': f"+998 90 {RNG.randint(100,999)}-{RNG.randint(10,99)}-{RNG.randint(10,99)}",
                    'capacity': cap, 'price_per_day': ppd,
                    'price_per_hour': (ppd // 8) if ppd else RNG.randrange(50000, 200000, 10000),
                    'working_hours_start': _t(9, 0), 'working_hours_end': _t(23, 0),
                    'is_active': True, 'latitude': _lat, 'longitude': _lng,
                    'cancel_penalty_percent': 10, 'grace_minutes': 15, 'prepay_required': True})
            n_v += 1
            # Mavjud joyga koordinata bo'lmasa — qo'shamiz (xaritada chiqishi uchun)
            if v.latitude is None or v.longitude is None:
                v.latitude, v.longitude = _lat, _lng
                v.save(update_fields=['latitude', 'longitude'])
            # Xizmat va ustalar (slot turlari uchun) — har doim ta'minlaymiz
            for si, (sname, sprice, sdur) in enumerate(SVC_TPL.get(vtype, [])):
                VenueService.objects.get_or_create(
                    venue=v, name=sname,
                    defaults={'price': sprice, 'duration_minutes': sdur, 'order': si})
            for si, (stname, stspec) in enumerate(STAFF_TPL.get(vtype, [])):
                stf, _sc = VenueStaff.objects.get_or_create(
                    venue=v, name=stname,
                    defaults={'specialty': stspec, 'order': si,
                              'rating': round(RNG.uniform(4.3, 4.9), 1),
                              'reviews_count': RNG.randint(12, 140),
                              'completed_count': RNG.randint(70, 650),
                              'experience_years': RNG.randint(2, 12),
                              'bio': f"{stspec or 'Tajribali mutaxassis'} — yuqori sifatli xizmat."})
                if not stf.reviews_count:  # eski ustaga statistika qo'shamiz
                    stf.rating = round(RNG.uniform(4.3, 4.9), 1)
                    stf.reviews_count = RNG.randint(12, 140)
                    stf.completed_count = RNG.randint(70, 650)
                    stf.experience_years = RNG.randint(2, 12)
                    stf.bio = stf.bio or f"{stspec or 'Tajribali mutaxassis'} — yuqori sifatli xizmat."
                    stf.save()
            # bir nechta bron (turli holat)
            today = date.today()
            for st, dd in [('confirmed', 7), ('pending', 14), ('completed', -10)]:
                bk, c = VenueBooking.objects.get_or_create(
                    venue=v, user=RNG.choice(citizens), booking_date=today + timedelta(days=dd),
                    defaults={'status': st, 'guests': RNG.randint(2, min(cap, 300)),
                              'event_type': RNG.choice(EVENTS) if vtype == 'wedding' else '',
                              'total_amount': ppd or RNG.randrange(100000, 800000, 50000),
                              'message': "Demo bron."})
                if c:
                    n_b += 1
        self.stdout.write(f"🏛  Venue (booking): {n_v} ta (+{n_b} bron)")

    # ── 5. TO'LOV MUASSASALARI ──────────────────────────────────────────────────
    def _seed_providers(self):
        from payments.models import Provider
        DATA = [
            ('kommunal', "Hududgaz — Shofirkon", 0), ('kommunal', "Elektr tarmoqlari", 0),
            ('kommunal', "Suv ta'minoti (Suvoqova)", 0), ('kommunal', "Issiqlik tarmog'i", 0),
            ('internet', "Uztelecom Internet", 75000), ('internet', "Beeline Home", 80000),
            ('internet', "UMS Mobil", 0), ('internet', "Ucell aloqa", 0),
            ('kurs', "English Zone — kurs to'lovi", 350000),
            ('kurs', "IT Park o'quv markazi", 500000),
            ('kurs', "Matematika repetitor markazi", 300000),
            ('bogcha', "Bolajon Bog'chasi", 450000), ('bogcha', "Kamalak MTM", 400000),
            ('maktab', "Bilim xususiy maktabi", 900000), ('maktab', "Istiqbol litseyi", 800000),
            ('boshqa', "Maishiy chiqindi (Tozalik)", 25000),
            ('boshqa', "Kabel TV — Shofirkon", 40000),
            ('boshqa', "Sug'urta — Gross Insurance", 0),
            ('kommunal', "Telefon aloqa (uy)", 0),
            ('internet', "Sarkor Telecom", 90000),
            ('kurs', "Koreys tili markazi", 320000),
            ('maktab', "Al-Xorazmiy maktabi", 850000),
        ]
        n = 0
        for cat, name, amount in DATA:
            _, c = Provider.objects.get_or_create(
                name=name,
                defaults={'category': cat, 'amount': amount, 'region': 'Shofirkon',
                          'description': "Shofirkon hududidagi to'lov muassasasi.",
                          'address': f"Shofirkon, {RNG.choice(['Markaziy', 'Navoiy', 'Bog'])} ko'chasi",
                          'phone': f"+998 65 {RNG.randint(200,599)}-{RNG.randint(10,99)}-{RNG.randint(10,99)}",
                          'is_active': True})
            if c:
                n += 1
        self.stdout.write(f"💳 To'lov muassasalari: {Provider.objects.count()} ta (+{n} yangi)")

    # ── 6. MARKETPLACE E'LONLARI ────────────────────────────────────────────────
    def _seed_ads(self, citizens):
        from main.models import Ad
        ADS = [
            ('uy_joy', "Shofirkon markazidan 2 xonali kvartira", 350000, 'fixed', "Markaz"),
            ('uy_joy', "Hovli uy sotiladi — 6 sotix", 420000000, 'negotiable', "Yangiobod MFY"),
            ('uy_joy', "Yangi qurilgan 3 xonali uy ijaraga", 2500000, 'fixed', "Bog' ko'chasi"),
            ('avtomobil', "Chevrolet Cobalt 2021 — ideal holat", 165000000, 'negotiable', "Markaz"),
            ('avtomobil', "Nexia 3 2018-yil sotiladi", 125000000, 'negotiable', "Vobkent yo'li"),
            ('avtomobil', "Spark 2019 — kam yurgan", 98000000, 'negotiable', "Markaz"),
            ('avtomobil', "Damas yuk tashish uchun", 89000000, 'fixed', "Bozor atrofi"),
            ('boshqa', "iPhone 14 Pro 128GB — ideal holat", 11500000, 'negotiable', "Markaz"),
            ('boshqa', "Samsung 55\" Smart TV — yangi quti", 5800000, 'fixed', "Elektronika bozori"),
            ('xizmat', "To'y videografi va fotograf", 1500000, 'negotiable', "Shofirkon"),
            ('boshqa', "Noutbuk Lenovo IdeaPad i5 16GB", 7200000, 'negotiable', "IT Park"),
            ('boshqa', "PlayStation 5 + 2 joystik", 6500000, 'negotiable', "Markaz"),
            ('xizmat', "Mebel yig'ish va ta'mirlash", 100000, 'negotiable', "Shahar bo'ylab"),
            ('uy_joy', "Tijorat ob'ekti ijaraga (do'kon)", 3500000, 'fixed', "Markaziy bozor"),
            ('avtomobil', "Lacetti 2016 — yaxshi holat", 105000000, 'negotiable', "Markaz"),
            ('hayvonlar', "German ovcharka kuchukchasi", 3500000, 'negotiable', "Yangiobod"),
            ('hayvonlar', "Tovuq va xo'roz (mahalliy zot)", 80000, 'fixed', "Fermer bozori"),
            ('hayvonlar', "Quyon bolalari sotiladi", 60000, 'fixed', "Qishloq"),
            ('xizmat', "Ingliz tili — IELTS tayyorlov", 400000, 'fixed', "English Zone"),
            ('uy_joy', "Garaj sotiladi — markazda", 45000000, 'negotiable', "Markaz"),
            ('avtomobil', "Malibu 2 — 2020-yil", 285000000, 'negotiable', "Markaz"),
            ('xizmat', "Tort va shirinliklar buyurtmaga", 150000, 'fixed', "Shofirkon"),
            ('xizmat', "Qurilish-ta'mirlash brigadasi", 200000, 'negotiable', "Shahar bo'ylab"),
            ('uy_joy', "Yer uchastkasi 10 sotix sotiladi", 180000000, 'negotiable', "Shofirkon chekkasi"),
        ]
        n = 0
        for i, (cat, title, price, ptype, loc) in enumerate(ADS):
            u = citizens[i % len(citizens)]
            if Ad.objects.filter(title=title).exists():
                continue
            Ad.objects.create(
                user=u, category=cat, title=title,
                description=f"{title}. Batafsil ma'lumot uchun qo'ng'iroq qiling. Shofirkon, {loc}.",
                price=price, price_type=ptype, location=f"Shofirkon, {loc}",
                contact_phone=u.phone, status='active', venue_booking_enabled=False)
            n += 1
        self.stdout.write(f"📋 Marketplace e'lonlari: +{n} ta (jami {Ad.objects.count()})")

    # ── 7. COMMUNITY: so'rovnomalar + yordam markazi ───────────────────────────
    def _seed_community(self, citizens):
        from main.models import (Poll, PollOption, PollVote, PollComment,
                                  Neighborhood, HelpRequest, HelpVolunteer)
        nbhds = list(Neighborhood.objects.all())

        POLLS = [
            ("Mahallada yangi bolalar maydonchasi kerakmi?", ["Ha, albatta", "Yo'q", "Farqi yo'q"]),
            ("Ko'cha yoritgichlari qaysi vaqtda yonsin?", ["18:00 dan", "19:00 dan", "20:00 dan"]),
            ("Hovli tozalash kunini qachon belgilaymiz?", ["Shanba", "Yakshanba", "Juma"]),
            ("Yangi avtobus marshruti kerakmi?", ["Ha, kerak", "Yo'q, yetarli"]),
            ("Mahalla chat qoidalari maqulmi?", ["Maqul", "O'zgartirish kerak"]),
            ("Suv ta'minoti jadvalini qabul qilamizmi?", ["Ha", "Yo'q", "Muhokama kerak"]),
        ]
        comments = ["Yaxshi tashabbus!", "Men qo'llab-quvvatlayman.",
                    "Muhim masala.", "Rozi emasman.", "Albatta kerak."]
        n_poll = n_help = 0
        for q, opts in POLLS:
            poll, created = Poll.objects.get_or_create(
                question=q,
                defaults={'creator': RNG.choice(citizens),
                          'neighborhood': (RNG.choice(nbhds) if nbhds else None),
                          'description': "Mahalla a'zolari uchun so'rovnoma.",
                          'poll_type': 'single', 'is_active': True})
            if created:
                n_poll += 1
                option_objs = [PollOption.objects.create(poll=poll, text=t, order=i)
                               for i, t in enumerate(opts)]
                for u in RNG.sample(citizens, RNG.randint(6, len(citizens))):
                    PollVote.objects.get_or_create(option=RNG.choice(option_objs), user=u)
                for u in RNG.sample(citizens, RNG.randint(1, 4)):
                    PollComment.objects.create(poll=poll, user=u, text=RNG.choice(comments))

        HELP = [
            ('request', 'blood', "Shoshilinch qon kerak (B+)", True),
            ('offer', 'volunteer', "Keksalarga oziq-ovqat yetkazaman", False),
            ('request', 'lost_found', "Mushuk yo'qoldi — Markaz mahallasi", False),
            ('request', 'elderly', "Qariya bobomga hamroh kerak", False),
            ('offer', 'donation', "Bolalar kiyimlarini ehson qilaman", False),
            ('request', 'emergency', "Quvur yorildi — usta kerak", True),
            ('offer', 'general', "Bepul ingliz tili darslari", False),
            ('request', 'general', "Ko'chada daraxt ekishga ko'ngillilar kerak", False),
        ]
        for kind, cat, title, urgent in HELP:
            lat = round(BASE_LAT + RNG.uniform(-0.03, 0.03), 6)
            lng = round(BASE_LNG + RNG.uniform(-0.03, 0.03), 6)
            hr, created = HelpRequest.objects.get_or_create(
                title=title,
                defaults={'creator': RNG.choice(citizens),
                          'neighborhood': (RNG.choice(nbhds) if nbhds else None),
                          'kind': kind, 'category': cat,
                          'description': title + ". Batafsil ma'lumot uchun bog'laning.",
                          'location': "Shofirkon markazi", 'latitude': lat, 'longitude': lng,
                          'phone': "+998 90 " + str(RNG.randint(100, 999)) + "-" + str(RNG.randint(10, 99)) + "-" + str(RNG.randint(10, 99)),
                          'status': RNG.choice(['open', 'open', 'in_progress', 'resolved']),
                          'is_urgent': urgent})
            if created:
                n_help += 1
                for u in RNG.sample(citizens, RNG.randint(0, 3)):
                    HelpVolunteer.objects.create(request=hr, user=u, message="Yordam beraman.")
        self.stdout.write("🗳  So'rovnomalar: +" + str(n_poll) + ", yordam so'rovlari: +" + str(n_help))

    # ── 8. TAKSI SAFARLARI (tarix + to'lov) ─────────────────────────────────────
    def _seed_taxi_trips(self, citizens):
        from taxi.models import Taxist, Trip, Payment
        taxists = list(Taxist.objects.all())
        if not taxists:
            return
        n = 0
        for u in RNG.sample(citizens, min(15, len(citizens))):
            tx = RNG.choice(taxists)
            route = tx.routes.first()
            pa = route.point_a if route else "Shofirkon markazi"
            pb = route.point_b if route else "Buxoro shahri"
            price = int(route.passenger_price) if route else RNG.randrange(10000, 50000, 1000)
            status = RNG.choice(['completed', 'completed', 'completed', 'cancelled', 'accepted'])
            paid = status == 'completed' and RNG.random() < 0.7
            trip, created = Trip.objects.get_or_create(
                passenger=u, taxist=tx, point_a=pa, point_b=pb,
                defaults={'route': route, 'price': price, 'status': status,
                          'payment_method': RNG.choice(['cash', 'card']),
                          'payment_status': 'paid' if paid else 'unpaid',
                          'completed_at': timezone.now() if status == 'completed' else None})
            if created:
                n += 1
                if paid:
                    Payment.objects.get_or_create(
                        trip=trip,
                        defaults={'user': u, 'amount': price, 'card_holder': u.name,
                                  'card_last4': str(RNG.randint(1000, 9999)),
                                  'card_brand': RNG.choice(['Uzcard', 'Humo', 'Visa']),
                                  'status': 'paid', 'paid_at': timezone.now()})
        self.stdout.write("🧾 Taksi safarlari: +" + str(n))

    # ── 9. DELIVERY HAYDOVCHILAR ────────────────────────────────────────────────
    def _seed_delivery_drivers(self, citizens):
        from delivery.models import DeliveryDriver
        VEH = ['moto', 'bike', 'car', 'foot']
        n = 0
        for u in RNG.sample(citizens, min(6, len(citizens))):
            _, c = DeliveryDriver.objects.get_or_create(
                user=u,
                defaults={'full_name': u.name, 'phone': u.phone,
                          'vehicle_type': RNG.choice(VEH),
                          'vehicle_number': str(RNG.randint(10, 99)) + " " + RNG.choice("ABCH") + str(RNG.randint(100, 999)) + RNG.choice("ABCH") + RNG.choice("ABCH"),
                          'is_available': RNG.random() < 0.6, 'is_active': True})
            if c:
                n += 1
        self.stdout.write("🛵 Delivery haydovchilar: +" + str(n))

    # ── 10. TO'LOV YOZUVLARI (payments tarixi) ──────────────────────────────────
    def _seed_service_payments(self, citizens):
        from payments.models import Provider, ServicePayment
        from datetime import date as _d
        providers = list(Provider.objects.all())
        if not providers:
            return
        this_month = _d.today().strftime('%Y-%m')
        n = 0
        for u in RNG.sample(citizens, min(18, len(citizens))):
            for p in RNG.sample(providers, RNG.randint(1, 3)):
                amount = int(p.amount) if p.amount else RNG.randrange(20000, 200000, 5000)
                _, c = ServicePayment.objects.get_or_create(
                    user=u, provider=p, period=this_month,
                    defaults={'provider_name': p.name, 'category': p.category,
                              'payer_name': u.name, 'amount': amount,
                              'card_last4': str(RNG.randint(1000, 9999)),
                              'card_brand': RNG.choice(['Uzcard', 'Humo']),
                              'status': 'paid', 'paid_at': timezone.now()})
                if c:
                    n += 1
        self.stdout.write("💸 To'lov yozuvlari: +" + str(n))

    # ── 11. ENGAGEMENT (sevimlilar) ─────────────────────────────────────────────
    def _seed_engagement(self, citizens):
        from main.models import Ad, AdFavorite
        from places.models import Place, PlaceFavorite
        ads = list(Ad.objects.filter(status='active')[:40])
        places = list(Place.objects.all()[:60])
        n = 0
        for u in RNG.sample(citizens, min(20, len(citizens))):
            for a in (RNG.sample(ads, min(len(ads), RNG.randint(1, 4))) if ads else []):
                _, c = AdFavorite.objects.get_or_create(ad=a, user=u)
                if c:
                    n += 1
            for pl in (RNG.sample(places, min(len(places), RNG.randint(1, 4))) if places else []):
                _, c = PlaceFavorite.objects.get_or_create(place=pl, user=u)
                if c:
                    n += 1
        self.stdout.write("❤️  Sevimlilar: +" + str(n))

    # ── HISOBOT ──────────────────────────────────────────────────────────────
    def _report(self):
        from places.models import Place
        from delivery.models import Store, Product
        from taxi.models import Taxist
        from booking.models import Venue
        from payments.models import Provider, ServicePayment
        from main.models import Ad, Poll, HelpRequest
        from taxi.models import Trip
        from delivery.models import DeliveryDriver
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("✅ Investor-demo ma'lumotlari tayyor!"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"  📍 Xarita joylari:   {Place.objects.count()}")
        self.stdout.write(f"  🛒 Do'konlar:        {Store.objects.count()}")
        self.stdout.write(f"  📦 Mahsulotlar:      {Product.objects.count()}")
        self.stdout.write(f"  🚖 Taksistlar:       {Taxist.objects.count()}")
        self.stdout.write(f"  🧾 Taksi safarlari:  {Trip.objects.count()}")
        self.stdout.write(f"  🛵 Delivery hayd.:   {DeliveryDriver.objects.count()}")
        self.stdout.write(f"  🏛  Venue (booking):  {Venue.objects.count()}")
        self.stdout.write(f"  💳 To'lov muassasa:  {Provider.objects.count()}")
        self.stdout.write(f"  💸 To'lov yozuvlari: {ServicePayment.objects.count()}")
        self.stdout.write(f"  🗳  So'rovnomalar:    {Poll.objects.count()}")
        self.stdout.write(f"  🤝 Yordam so'rovlar: {HelpRequest.objects.count()}")
        self.stdout.write(f"  📋 E'lonlar:         {Ad.objects.count()}")
        self.stdout.write("\n  Parol (barcha demo hisoblar): demo1234")
        self.stdout.write("  Ishga tushirish: python manage.py runserver → http://127.0.0.1:8000/\n")

    # ── TOZALASH ────────────────────────────────────────────────────────────────
    def _clear(self):
        self.stdout.write("🗑  seed_demo_full ma'lumotlari o'chirilmoqda...")
        # Shu buyruq yaratgan foydalanuvchilar prefiksi: +99893 / +99895 / +99897
        qs = User.objects.filter(phone__regex=r'^\+9989[357]\d{7}$')
        qs.delete()  # bog'liq do'kon/taksist/e'lon/bron CASCADE bilan o'chadi
        self.stdout.write(self.style.SUCCESS("  ✅ Tozalandi (qolgan seedlar saqlanib qoldi)."))
