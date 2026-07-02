"""
Demo seed — mahalla do'konlari funksiyalarini QO'LDA sinash uchun.

Yaratadi: do'kon egasi + 2 mijoz, 2 do'kon (biri to'liq + pickup, biri sodda),
har xil holatdagi mahsulotlar (mavjud / narxi yangilangan / tugagan+sekundomer /
tugagan+sanasiz), yangiliklar tasmasi, obuna, chat suhbati va turli bosqichdagi
pickup buyurtmalari.

Idempotent: bir necha marta ishga tushirilsa dublikat yaratmaydi.
Faqat DEBUG muhitida ishlaydi (production himoyasi) — `--force` bilan majburlash mumkin.

Ishga tushirish:
    python manage.py seed_demo_shops
"""
from datetime import timedelta
from io import BytesIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.text import slugify

from delivery.models import (
    DeliveryCategory, Store, StoreImage, Product, ProductImage,
    StoreUpdate, StoreSubscription, StoreChatThread, StoreChatMessage,
    Order, OrderItem,
)
from delivery.feed import create_store_update
from delivery.chat import get_or_create_thread, create_message

User = get_user_model()

# ── Demo hisoblar (telefon, ism, rol, parol bir xil: demo12345) ──────────────
OWNER = ('+998900000010', 'Aziz Karimov', 'business')
CUSTOMERS = [
    ('+998900000011', 'Dilnoza Yusupova'),
    ('+998900000012', 'Sardor Aliyev'),
]
DEMO_PASSWORD = 'demo12345'

# Placeholder rasm ranglari
COLORS = ['#16A34A', '#2563EB', '#DB2777', '#D97706', '#7C3AED', '#0891B2']


def _make_image(text, color='#16A34A', size=(600, 600)):
    """PIL bilan oddiy rangli placeholder rasm (internetsiz)."""
    from PIL import Image, ImageDraw
    img = Image.new('RGB', size, color)
    draw = ImageDraw.Draw(img)
    # Matnni taxminan markazga joylashtiramiz (default shrift bilan).
    draw.text((size[0] // 2 - len(text) * 4, size[1] // 2 - 8), text, fill='white')
    buf = BytesIO()
    img.save(buf, format='PNG')
    return ContentFile(buf.getvalue())


class Command(BaseCommand):
    help = "Do'kon funksiyalarini qo'lda sinash uchun to'liq demo ma'lumot (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help="DEBUG=False bo'lsa ham majburlab ishga tushirish.")

    def handle(self, *args, **opts):
        if not settings.DEBUG and not opts['force']:
            raise CommandError(
                "Bu buyruq faqat DEBUG=True muhitida ishlaydi. "
                "Majburlash uchun --force bering (ehtiyot bo'ling!)."
            )

        self.stdout.write(self.style.MIGRATE_HEADING("SamCity demo do'konlar seed..."))

        owner = self._user(*OWNER)
        customers = [self._user(phone, name, 'user') for phone, name in CUSTOMERS]

        cat_food = self._category('Oziq-ovqat')
        cat_market = self._category('Bozor')

        # ── 1) To'liq do'kon (pickup yoqilgan) ───────────────────────────────
        aziz = self._store(
            owner=owner, name="Aziz do'koni", category=cat_food,
            description="Mahalladagi eng qulay do'kon — yangi mahsulotlar har kuni.",
            address="Shofirkon, Markaziy ko'cha 10", phone='+998 90 123 45 67',
            working_hours="9:00–22:00, har kuni",
            owner_bio="Assalomu alaykum! Men Aziz — 10 yildan beri mahallamizga xizmat qilaman. "
                      "Sifat va halollik — asosiy tamoyilim.",
            pickup_enabled=True, with_media=True,
        )

        # ── 2) Sodda do'kon (pickup yoqilmagan) ──────────────────────────────
        tez = self._store(
            owner=owner, name="Tez bozor", category=cat_market,
            description="Tez va arzon xaridlar.",
            address="Shofirkon, Bozor ko'chasi 3", phone='+998 90 765 43 21',
            working_hours="8:00–20:00", owner_bio='', pickup_enabled=False, with_media=False,
        )

        now = timezone.now()

        # ── Mahsulotlar: Aziz do'koni (holatlar aralash) ─────────────────────
        p_norm1 = self._product(aziz, "Sut 1L", 12000, 40)
        p_norm2 = self._product(aziz, "Non (tandir)", 4000, 100)
        p_norm3 = self._product(aziz, "Tuxum 10 dona", 18000, 25)
        p_price = self._product(aziz, "Guruch Lazer 1kg", 20000, 30)
        # Tugagan + sekundomer (2 va 3 kundan keyin keladi)
        p_oos1 = self._product(aziz, "Yog' Oltin 1L", 24000, 0,
                               restock_at=now + timedelta(days=2, hours=5))
        p_oos2 = self._product(aziz, "Shakar 1kg", 13000, 0,
                               restock_at=now + timedelta(days=3, hours=2))
        # Tugagan + sana belgilanmagan
        p_oos3 = self._product(aziz, "Asal 0.5kg", 55000, 0, restock_at=None)

        # Tez bozor mahsulotlari (soddaroq)
        self._product(tez, "Coca-Cola 1L", 12000, 50)
        self._product(tez, "Suv 1.5L", 4000, 120)
        self._product(tez, "Sok 1L", 15000, 40)
        self._product(tez, "Pechenye", 9000, 60)
        self._product(tez, "Choy 100g", 17000, 35)
        self._product(tez, "Konfet 1kg", 32000, 20)

        # ── Obuna (mijoz1 → Aziz do'koni) — feed hodisalaridan OLDIN ─────────
        StoreSubscription.objects.get_or_create(
            store=aziz, user=customers[0], defaults={'is_enabled': True})

        # ── Yangiliklar tasmasi + bildirishnoma (idempotent) ─────────────────
        # create_store_update() obunachiga (mijoz1) bildirishnoma yuboradi.
        if not aziz.updates.exists():
            create_store_update(aziz, 'price_changed', product=p_price,
                                old_price=22000, new_price=20000,
                                text="Narx tushdi: Guruch Lazer 1kg")
            create_store_update(aziz, 'announcement',
                                text="Bugundan boshlab do'konimizda sut mahsulotlari ham bor! 🥛")
        if not tez.updates.exists():
            create_store_update(tez, 'announcement',
                                text="Yangi yil chegirmalari boshlandi! 🎉")

        # ── Chat suhbati (mijoz1 ↔ Aziz do'koni) ─────────────────────────────
        thread = get_or_create_thread(aziz, customers[0])
        if not thread.messages.exists():
            create_message(thread, customers[0], "Assalomu alaykum, asal bormi?")
            create_message(thread, owner, "Va alaykum assalom! Hozircha tugagan, ertага keladi.")
            create_message(thread, customers[0], "Rahmat, ertaga kelaman!")

        # ── Pickup buyurtmalari (turli bosqichlarda) ─────────────────────────
        norders = 0
        norders += self._pickup_order(
            customers[0], aziz, [(p_norm1, 2), (p_norm2, 3)],
            marker='demo-pickup-accepted', status='accepted')
        norders += self._pickup_order(
            customers[0], aziz, [(p_norm3, 1)],
            marker='demo-pickup-ready', status='ready',
            ready_at=now - timedelta(minutes=15))
        norders += self._pickup_order(
            customers[1], aziz, [(p_norm2, 5)],
            marker='demo-pickup-done', status='delivered',
            ready_at=now - timedelta(hours=2), confirmed_at=now - timedelta(hours=1))

        self._summary(owner, customers, [aziz, tez], norders)

    # ── Yordamchilar ─────────────────────────────────────────────────────────
    def _user(self, phone, name, role):
        # Dedikatsiya qilingan demo hisoblar — ism/rol/parolni har safar
        # kafolatlaymiz (oldingi seed'lardan qolgan bo'lsa ham to'g'rilanadi).
        user, _ = User.objects.get_or_create(phone=phone, defaults={'name': name})
        user.name = name
        user.role = role
        user.is_active = True
        user.set_password(DEMO_PASSWORD)
        user.save()
        return user

    def _category(self, name):
        cat, _ = DeliveryCategory.objects.get_or_create(
            slug=slugify(name), defaults={'name': name})
        return cat

    def _store(self, *, owner, name, category, description, address, phone,
               working_hours, owner_bio, pickup_enabled, with_media):
        store, _ = Store.objects.get_or_create(
            owner=owner, name=name,
            defaults={
                'category': category, 'description': description, 'address': address,
                'phone': phone, 'working_hours': working_hours, 'owner_bio': owner_bio,
                'pickup_enabled': pickup_enabled, 'is_active': True,
                'latitude': 40.117, 'longitude': 64.512,
            },
        )
        # Mavjud do'konni ham yangilab qo'yamiz (qayta ishga tushirishda to'g'ri holat).
        Store.objects.filter(pk=store.pk).update(
            category=category, description=description, address=address, phone=phone,
            working_hours=working_hours, owner_bio=owner_bio,
            pickup_enabled=pickup_enabled, is_active=True)
        store.refresh_from_db()

        if with_media:
            if not store.logo:
                store.logo.save(f'{slugify(name)}-logo.png',
                                _make_image(name, COLORS[0]), save=False)
            if not store.owner_photo:
                store.owner_photo.save(f'{slugify(name)}-owner.png',
                                       _make_image('Egasi', COLORS[4]), save=False)
            store.save()
            # Galereya (4 ta) — faqat bo'sh bo'lsa
            if store.images.count() == 0:
                for i in range(4):
                    img = StoreImage(store=store)
                    img.image.save(f'{slugify(name)}-g{i}.png',
                                   _make_image(f'Rasm {i+1}', COLORS[i % len(COLORS)]),
                                   save=False)
                    img.save()
        return store

    def _product(self, store, name, price, stock, restock_at=None):
        product, created = Product.objects.get_or_create(
            store=store, name=name,
            defaults={'price': price, 'stock': stock, 'is_available': True,
                      'restock_at': restock_at},
        )
        if not created:
            Product.objects.filter(pk=product.pk).update(
                price=price, stock=stock, is_available=True, restock_at=restock_at)
            product.refresh_from_db()
        # Bitta rasm (bo'sh bo'lsa)
        if product.images.count() == 0:
            pi = ProductImage(product=product)
            pi.image.save(f'{slugify(name)}.png',
                          _make_image(name, COLORS[hash(name) % len(COLORS)]), save=False)
            pi.save()
        return product

    def _pickup_order(self, customer, store, lines, *, marker, status,
                      ready_at=None, confirmed_at=None):
        """Pickup buyurtma yaratadi (marker orqali idempotent)."""
        if Order.objects.filter(user=customer, note=marker).exists():
            return 0
        subtotal = sum(int(p.price) * qty for p, qty in lines)
        order = Order.objects.create(
            user=customer, full_name=customer.name, phone=customer.phone,
            address='', note=marker, subtotal=subtotal, delivery_fee=0, total=subtotal,
            status=status, payment_method='card', payment_status='paid',
            card_last4='1234', card_brand='Uzcard',
            fulfillment_type='pickup',
            ready_for_pickup_at=ready_at, customer_confirmed_at=confirmed_at,
        )
        for p, qty in lines:
            OrderItem.objects.create(
                order=order, product=p, product_name=p.name,
                store_name=store.name, price=p.price, quantity=qty)
        return 1

    def _summary(self, owner, customers, stores, norders):
        s = self.style
        self.stdout.write('')
        self.stdout.write(s.SUCCESS('═══════════════════════════════════════════════'))
        self.stdout.write(s.SUCCESS('  ✅ DEMO MA\'LUMOTLAR TAYYOR'))
        self.stdout.write(s.SUCCESS('═══════════════════════════════════════════════'))
        self.stdout.write('')
        self.stdout.write(s.HTTP_INFO('👤 HISOBLAR (parol hammasida: %s)' % DEMO_PASSWORD))
        self.stdout.write(f"   Do'kon egasi : {owner.phone}  — {owner.name}")
        for c in customers:
            self.stdout.write(f"   Mijoz        : {c.phone}  — {c.name}")
        self.stdout.write('')
        self.stdout.write(s.HTTP_INFO("🏪 DO'KONLAR"))
        for st in stores:
            pk_url = f"/delivery/{st.pk}/"
            pickup = 'pickup YOQILGAN' if st.pickup_enabled else 'pickup yoqilmagan'
            self.stdout.write(
                f"   #{st.pk}  {st.name}  ({pickup})  → {pk_url}  "
                f"[{st.products.count()} mahsulot]")
        self.stdout.write('')
        self.stdout.write(s.HTTP_INFO('📊 QO\'SHILDI'))
        self.stdout.write(f"   Mahsulotlar : {Product.objects.filter(store__in=stores).count()}")
        self.stdout.write(f"   Yangiliklar : {StoreUpdate.objects.filter(store__in=stores).count()}")
        self.stdout.write(f"   Obunalar    : {StoreSubscription.objects.filter(store__in=stores).count()}")
        self.stdout.write(f"   Chat xabar  : {StoreChatMessage.objects.filter(thread__store__in=stores).count()}")
        self.stdout.write(f"   Pickup buyurtma (yangi): {norders}")
        self.stdout.write('')
        self.stdout.write(s.WARNING('   Do\'konlar ro\'yxati: /delivery/'))
        self.stdout.write('')
