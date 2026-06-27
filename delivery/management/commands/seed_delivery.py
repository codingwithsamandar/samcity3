import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify

from delivery.models import DeliveryCategory, Store, Product, Order, OrderItem

User = get_user_model()

DEMO_BUYERS = [
    ('+998900000001', 'Jasur'), ('+998900000002', 'Dilnoza'),
    ('+998900000003', 'Otabek'), ('+998900000004', 'Malika'),
    ('+998900000005', 'Rustam'),
]
ORDER_STATUSES = ['pending', 'accepted', 'preparing', 'ready', 'delivered']


CATEGORIES = [
    'Oziq-ovqat', 'Dorixona', 'Restoran', 'Gullar', 'Non mahsulotlari', 'Ichimliklar',
]

# store: (name, category, description, address, phone, [ (product, price, stock), ... ])
STORES = [
    ('Shofirkon Market', 'Oziq-ovqat', "Oziq-ovqat va kundalik mahsulotlar.", "Shofirkon, Markaziy ko'cha 1", '+998 90 111 00 11', [
        ('Guruch Lazer 1kg', 18000, 50), ('Yog\' Oltin 1L', 22000, 40),
        ('Shakar 1kg', 12000, 60), ('Tuxum 10 dona', 16000, 30),
    ]),
    ('Sog\'lik Dorixona', 'Dorixona', "Dori-darmon va tibbiy vositalar.", "Shofirkon, Tibbiyot ko'chasi 5", '+998 90 222 00 22', [
        ('Parasetamol', 8000, 100), ('Vitamin C', 25000, 40),
        ('Niqob (50 dona)', 30000, 20),
    ]),
    ('Osh Markazi', 'Restoran', "Milliy taomlar, yetkazib berish.", "Shofirkon, Bog' ko'chasi 12", '+998 90 333 00 33', [
        ('Osh (1 porsiya)', 28000, 100), ('Manti (5 dona)', 25000, 80),
        ('Lag\'mon', 26000, 50), ('Somsa', 6000, 200),
    ]),
    ('Gulzor', 'Gullar', "Yangi gullar va buketlar.", "Shofirkon, Gulzor 3", '+998 90 444 00 44', [
        ('Atirgul (1 dona)', 12000, 150), ('Buket "Sevgi"', 180000, 10),
    ]),
    ('Tandir Non', 'Non mahsulotlari', "Issiq tandir non va patir.", "Shofirkon, Non bozori", '+998 90 555 00 55', [
        ('Tandir non', 4000, 300), ('Patir', 8000, 100),
    ]),
    ('Cool Drinks', 'Ichimliklar', "Sovuq ichimliklar va suvlar.", "Shofirkon, Markaz", '+998 90 666 00 66', [
        ('Coca-Cola 1L', 12000, 80), ('Suv 1.5L', 4000, 200), ('Sok 1L', 15000, 60),
    ]),
]


class Command(BaseCommand):
    help = "Yetkazib berish (delivery) bo'limi uchun demo do'kon va mahsulotlar."

    def handle(self, *args, **opts):
        # Do'kon egasi (business foydalanuvchi)
        owner, created = User.objects.get_or_create(
            phone='+998900000010',
            defaults={'name': 'Demo Biznes', 'role': 'business'},
        )
        if created:
            owner.set_password('demo12345')
            owner.save()

        # Kategoriyalar
        cat_map = {}
        for name in CATEGORIES:
            cat, _ = DeliveryCategory.objects.get_or_create(
                slug=slugify(name), defaults={'name': name},
            )
            cat_map[name] = cat
        self.stdout.write(f"✓ {len(cat_map)} ta kategoriya")

        # Do'konlar + mahsulotlar
        nstores = nprod = 0
        for name, cat_name, desc, addr, phone, products in STORES:
            store, _ = Store.objects.update_or_create(
                name=name,
                defaults={
                    'owner': owner, 'category': cat_map.get(cat_name),
                    'description': desc, 'address': addr, 'phone': phone,
                    'is_active': True,
                },
            )
            nstores += 1
            for pname, price, stock in products:
                Product.objects.update_or_create(
                    store=store, name=pname,
                    defaults={'price': price, 'stock': stock, 'is_available': True},
                )
                nprod += 1

        # Demo xaridorlar
        buyers = []
        for phone, name in DEMO_BUYERS:
            u, c = User.objects.get_or_create(phone=phone, defaults={'name': name, 'role': 'user'})
            if c:
                u.set_password('demo12345')
                u.save()
            buyers.append(u)

        # Demo buyurtmalar (buyurtma paneli va tarix uchun)
        random.seed(7)
        norders = 0
        all_products = list(Product.objects.select_related('store').all())
        for i, buyer in enumerate(buyers):
            if not all_products:
                break
            picks = random.sample(all_products, min(2, len(all_products)))
            subtotal = sum(int(p.price) for p in picks)
            delivery_fee = 10000
            status = ORDER_STATUSES[i % len(ORDER_STATUSES)]
            paid = status != 'pending'
            order, created = Order.objects.get_or_create(
                user=buyer, address=f"Shofirkon, {i+1}-uy", phone=buyer.phone or '+998900000000',
                defaults={
                    'full_name': buyer.name, 'note': '',
                    'subtotal': subtotal, 'delivery_fee': delivery_fee, 'total': subtotal + delivery_fee,
                    'status': status, 'payment_method': 'card' if paid else 'cash',
                    'payment_status': 'paid' if paid else 'unpaid',
                    'card_last4': '1234' if paid else '', 'card_brand': 'Uzcard' if paid else '',
                    'created_at': timezone.now(),
                },
            )
            if created:
                for p in picks:
                    OrderItem.objects.create(
                        order=order, product=p, product_name=p.name,
                        store_name=p.store.name, price=p.price, quantity=random.randint(1, 3),
                    )
                norders += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ {nstores} ta do'kon, {nprod} ta mahsulot, {norders} ta buyurtma tayyor! Sahifa: /delivery/"
        ))
