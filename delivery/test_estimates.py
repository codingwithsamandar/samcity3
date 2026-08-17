"""Yetkazish vaqti taxmini — masofa va haqiqiy tezlikdan.

    python manage.py test delivery.test_estimates
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from main.models import User
from delivery.models import (
    Store, Product, Order, OrderItem, DeliveryDriver, DeliveryCategory,
)
from delivery.estimates import (
    haversine_km, order_distance_km, estimate_delivery_minutes,
    estimate_label, measured_speed, DEFAULT_SPEED, PICKUP_OVERHEAD_MIN,
    MIN_SAMPLES,
)

# Do'kon va mijoz — ~2 km oraliqda
STORE = (40.1156, 64.5036)
MIJOZ = (40.1336, 64.5036)   # ~2 km shimolda


class HaversineTests(TestCase):
    def test_same_point_is_zero(self):
        self.assertEqual(round(haversine_km(*STORE, *STORE), 3), 0)

    def test_known_distance(self):
        km = haversine_km(*STORE, *MIJOZ)
        self.assertAlmostEqual(km, 2.0, delta=0.15)


class DeliveryEstimateTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(phone='+998910001001', password='x', is_active=True)
        self.mijoz = User.objects.create_user(phone='+998910001002', password='x', is_active=True)
        self.kuryer_user = User.objects.create_user(phone='+998910001003', password='x', is_active=True)
        self.cat = DeliveryCategory.objects.create(name='Oziq-ovqat')
        self.store = Store.objects.create(
            owner=self.owner, name='Anor', category=self.cat,
            latitude=STORE[0], longitude=STORE[1])
        self.product = Product.objects.create(store=self.store, name='Non', price=5000)
        self.driver = DeliveryDriver.objects.create(
            user=self.kuryer_user, full_name='Ali', phone='+998910001003',
            vehicle_type='moto')

    def _order(self, lat=MIJOZ[0], lng=MIJOZ[1], **kw):
        o = Order.objects.create(
            user=self.mijoz, address='Manzil', phone='+998910001002',
            latitude=lat, longitude=lng, **kw)
        OrderItem.objects.create(order=o, product=self.product,
                                 product_name='Non', price=5000, quantity=1)
        return o

    # ── Masofa ──────────────────────────────────────────────────────────────
    def test_distance_includes_road_factor(self):
        km = order_distance_km(self._order())
        self.assertGreater(km, 2.0)      # to'g'ri chiziqdan uzunroq
        self.assertLess(km, 3.2)

    def test_no_distance_without_customer_coords(self):
        self.assertIsNone(order_distance_km(self._order(lat=None, lng=None)))

    def test_no_distance_without_store_coords(self):
        self.store.latitude = None
        self.store.save(update_fields=['latitude'])
        self.assertIsNone(order_distance_km(self._order()))

    # ── Taxmin ──────────────────────────────────────────────────────────────
    def test_estimate_uses_default_speed_without_history(self):
        minutes, km, source = estimate_delivery_minutes(self._order(), 'moto')
        self.assertEqual(source, 'default')
        kutilgan = round(km / DEFAULT_SPEED['moto'] * 60) + PICKUP_OVERHEAD_MIN
        self.assertEqual(minutes, kutilgan)

    def test_slower_vehicle_takes_longer(self):
        o = self._order()
        velosiped = estimate_delivery_minutes(o, 'bike')[0]
        moto = estimate_delivery_minutes(o, 'moto')[0]
        self.assertGreater(velosiped, moto)

    def test_estimate_none_without_coords(self):
        minutes, km, source = estimate_delivery_minutes(
            self._order(lat=None, lng=None), 'moto')
        self.assertIsNone(minutes)

    def test_label_shows_km_and_minutes(self):
        label = estimate_label(self._order(), 'moto')
        self.assertIn('km', label)
        self.assertIn('daqiqa', label)

    def test_minimum_five_minutes(self):
        """Juda yaqin manzil ham 5 daqiqadan kam bo'lmaydi."""
        minutes, _, _ = estimate_delivery_minutes(
            self._order(lat=STORE[0], lng=STORE[1]), 'moto')
        self.assertGreaterEqual(minutes, 5)

    # ── Haqiqiy tezlikdan o'rganish ─────────────────────────────────────────
    def _tarix(self, n, minutlar):
        now = timezone.now()
        for i in range(n):
            o = self._order(status='delivered', driver=self.driver)
            o.assigned_at = now - timedelta(days=i + 1, minutes=minutlar)
            o.delivered_at = now - timedelta(days=i + 1)
            o.save(update_fields=['assigned_at', 'delivered_at'])

    def test_measured_speed_none_below_min_samples(self):
        self._tarix(MIN_SAMPLES - 1, 10)
        self.assertIsNone(measured_speed('moto'))

    def test_measured_speed_used_when_enough_history(self):
        self._tarix(MIN_SAMPLES + 2, 10)
        self.assertIsNotNone(measured_speed('moto'))
        self.assertEqual(estimate_delivery_minutes(self._order(), 'moto')[2], 'measured')

    def test_fast_history_shortens_estimate(self):
        """Kuryerlar tez yetkazsa — taxmin ham qisqaradi."""
        standart = estimate_delivery_minutes(self._order(), 'moto')[0]
        self._tarix(MIN_SAMPLES + 2, 4)      # ~2.6 km ni 4 daqiqada
        tez = estimate_delivery_minutes(self._order(), 'moto')[0]
        self.assertLess(tez, standart)

    def test_absurd_durations_ignored(self):
        """Kunlab ochiq qolgan buyurtma tezlik o'lchoviga kirmaydi."""
        self._tarix(MIN_SAMPLES + 2, 600)    # 10 soat
        self.assertIsNone(measured_speed('moto'))

    def test_history_is_per_vehicle_type(self):
        self._tarix(MIN_SAMPLES + 2, 10)
        self.assertIsNotNone(measured_speed('moto'))
        self.assertIsNone(measured_speed('car'))
