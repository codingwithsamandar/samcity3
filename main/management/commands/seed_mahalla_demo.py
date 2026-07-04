"""Mahalla bo'limi uchun demo ma'lumot — do'konlar, joylar, so'rovnoma, e'lon.

Har bir (mavjud) mahallaga:
  • mahalla do'koni (olib ketish rejimi) + mahsulotlar,
  • maktab, bog'cha va ovqatlanish joyi (xaritada ko'rinadi),
  • rasmiy e'lon,
  • «Bepul o'quv kursi» so'rovnomasi (Ha / Yo'q + izoh),
  • ko'ngillilik (valentyorlik) taklifi
qo'shadi. Demo admin (+998900000001) har bir mahallaga admin qilinadi, shuning
uchun mobil ilovada so'rovnoma/e'lon ochish tugmalari ko'rinadi.

Idempotent — bir necha marta ishga tushirsa dublikat yaratmaydi.

    python manage.py seed_mahallas       # avval mahallalar bo'lishi kerak
    python manage.py seed_mahalla_demo
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from main.models import (
    Neighborhood, NeighborhoodAnnouncement, ChatAdmin, ChatRoom,
    Poll, PollOption,
)

User = get_user_model()
DEMO_PASSWORD = 'demo12345'

# Har bir mahalla do'koniga qo'shiladigan namuna mahsulotlar (nom, narx, zaxira).
PRODUCTS = [
    ("Non (tandir)", 4000, 100),
    ("Sut 1L", 12000, 40),
    ("Tuxum 10 dona", 18000, 25),
    ("Guruch 1kg", 20000, 30),
    ("Shakar 1kg", 13000, 50),
]


class Command(BaseCommand):
    help = "Mahalla bo'limi uchun demo do'kon/joy/so'rovnoma ma'lumotlari (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help="DEBUG=False bo'lsa ham ishga tushiradi.")
        parser.add_argument('--limit', type=int, default=5,
                            help="Nechta mahallaga demo qo'shilsin (default 5).")

    def handle(self, *args, **opts):
        if not settings.DEBUG and not opts['force']:
            raise CommandError("Bu buyruq faqat DEBUG=True da ishlaydi (--force bilan majburlang).")

        from delivery.models import Store, Product, DeliveryCategory
        from places.models import Place

        neighborhoods = list(Neighborhood.objects.all()[:opts['limit']])
        if not neighborhoods:
            raise CommandError("Mahalla topilmadi. Avval: python manage.py seed_mahallas")

        admin = self._user('+998900000001', 'Mahalla Admin', 'admin', is_staff=True)
        cat_food, _ = DeliveryCategory.objects.get_or_create(
            slug=slugify('Oziq-ovqat'), defaults={'name': 'Oziq-ovqat'})

        n_stores = n_products = n_places = n_polls = n_ann = n_help = 0

        for idx, nb in enumerate(neighborhoods):
            # Admin — shu mahallaga admin (so'rovnoma/e'lon ochish uchun)
            ChatAdmin.objects.get_or_create(neighborhood=nb, user=admin)
            ChatRoom.objects.get_or_create(neighborhood=nb)

            center = nb.centroid() or [nb.center_lat or 40.1156, nb.center_lng or 64.5036]
            clat, clng = center[0], center[1]

            # ── Mahalla do'koni ──────────────────────────────────────────────
            owner = self._user(f'+9989000001{idx:02d}', f"{nb.name} do'kondori", 'business')
            store, created = Store.objects.get_or_create(
                owner=owner, name=f"{nb.name} do'koni",
                defaults={
                    'store_type': 'mahalla', 'neighborhood': nb, 'category': cat_food,
                    'description': f"{nb.name} mahallasidagi qulay do'kon.",
                    'address': f"{nb.name}, Markaziy ko'cha", 'phone': '+998 90 123 45 67',
                    'working_hours': '8:00–22:00', 'pickup_enabled': True, 'is_active': True,
                    'latitude': clat, 'longitude': clng,
                },
            )
            if not created:
                Store.objects.filter(pk=store.pk).update(
                    store_type='mahalla', neighborhood=nb, pickup_enabled=True,
                    is_active=True, latitude=clat, longitude=clng)
            n_stores += int(created)

            for name, price, stock in PRODUCTS:
                _, pc = Product.objects.get_or_create(
                    store=store, name=name,
                    defaults={'price': price, 'stock': stock, 'is_available': True})
                n_products += int(pc)

            # ── Joylar (maktab / bog'cha / ovqatlanish) ─────────────────────
            demo_places = [
                ('school', f"{nb.name} maktabi", 0.001, 0.001),
                ('kindergarten', f"{nb.name} bog'chasi", -0.001, 0.001),
                ('restaurant', f"{nb.name} milliy taomlar", 0.001, -0.001),
            ]
            for category, pname, dlat, dlng in demo_places:
                plat, plng = self._inside(nb, clat + dlat, clng + dlng, clat, clng)
                _, plc = Place.objects.get_or_create(
                    name=pname, category=category,
                    defaults={'latitude': plat, 'longitude': plng,
                              'address': f"{nb.name} mahallasi", 'is_active': True})
                n_places += int(plc)

            # ── Rasmiy e'lon ────────────────────────────────────────────────
            _, ac = NeighborhoodAnnouncement.objects.get_or_create(
                neighborhood=nb, title="Mahalla yangiligi",
                defaults={'text': "Hurmatli mahalladoshlar! Shanba kuni umumiy "
                                  "hashar o'tkaziladi. Barchangizni kutamiz.",
                          'created_by': admin})
            n_ann += int(ac)

            # ── So'rovnoma (Ha / Yo'q) ──────────────────────────────────────
            question = "Mahallada bepul o'quv kurs tashkil qilaylikmi?"
            poll = Poll.objects.filter(neighborhood=nb, question=question).first()
            if poll is None:
                poll = Poll.objects.create(
                    neighborhood=nb, creator=admin, question=question,
                    description="Yoshlar uchun ingliz tili va kompyuter savodxonligi kurslari. "
                                "Fikringizni bildiring va izoh qoldiring.",
                    poll_type='single')
                PollOption.objects.create(poll=poll, text='Ha', order=0)
                PollOption.objects.create(poll=poll, text="Yo'q", order=1)
                PollOption.objects.create(poll=poll, text='Farqi yo\'q', order=2)
                n_polls += 1

            # ── Ko'ngillilik (valentyorlik) taklifi ─────────────────────────
            try:
                from main.models import HelpRequest
                _, hc = HelpRequest.objects.get_or_create(
                    creator=admin, neighborhood=nb, title="Keksalarga yordam",
                    defaults={'description': "Mahalladagi yolg'iz keksalarga oziq-ovqat va "
                                            "dori yetkazishda ko'ngillilar kerak.",
                              'kind': 'request', 'category': 'volunteer'})
                n_help += int(hc)
            except Exception:
                pass

        self.stdout.write(self.style.SUCCESS(
            f"Demo tayyor: {len(neighborhoods)} mahalla — "
            f"{n_stores} do'kon, {n_products} mahsulot, {n_places} joy, "
            f"{n_ann} e'lon, {n_polls} so'rovnoma, {n_help} ko'ngillilik."))
        self.stdout.write(self.style.HTTP_INFO(
            f"Admin: +998900000001  (parol: {DEMO_PASSWORD}) — barcha mahallaga admin."))

    # ── Yordamchilar ─────────────────────────────────────────────────────────
    def _user(self, phone, name, role, is_staff=False):
        user, _ = User.objects.get_or_create(phone=phone, defaults={'name': name})
        user.name = name
        user.role = role
        user.is_active = True
        if is_staff:
            user.is_staff = True
        user.set_password(DEMO_PASSWORD)
        user.save()
        return user

    def _inside(self, nb, lat, lng, clat, clng):
        """Chegara ichidagi nuqta — ofsetli nuqta tashqarida bo'lsa markazga qaytadi."""
        if nb.contains_point(lat, lng):
            return lat, lng
        return clat, clng
