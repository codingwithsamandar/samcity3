"""Kuryer (yetkazib beruvchi) mobil API testlari."""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from main.models import User
from delivery.models import DeliveryDriver, Order


def make_user(phone):
    return User.objects.create_user(phone=phone, password='Test12345!', is_active=True)


def make_order(user, driver=None, status='ready', fee=10000,
               fulfillment_type='delivery', **extra):
    return Order.objects.create(
        user=user, full_name='Mijoz', phone='+998900000000',
        address='Test manzil', subtotal=50000, delivery_fee=fee,
        total=50000 + fee, status=status, driver=driver,
        fulfillment_type=fulfillment_type, **extra,
    )


class CourierAPITests(TestCase):
    def setUp(self):
        self.customer = make_user('+998936100001')
        self.driver_user = make_user('+998936100002')
        self.driver = DeliveryDriver.objects.create(
            user=self.driver_user, full_name='Kuryer', phone='+998936100002',
            is_available=True)
        self.c = APIClient()
        self.c.force_authenticate(self.driver_user)

    # ── Ro'yxatdan o'tish ──
    def test_register_creates_driver_and_role(self):
        u = make_user('+998936100010')
        c = APIClient(); c.force_authenticate(u)
        r = c.post(reverse('api:courier-register'), {
            'full_name': 'Yangi kuryer', 'phone': '+998936100010',
            'vehicle_type': 'bike'}, format='json')
        self.assertEqual(r.status_code, 201)
        u.refresh_from_db()
        self.assertEqual(u.role, 'driver')
        self.assertTrue(DeliveryDriver.objects.filter(user=u).exists())

    def test_register_twice_rejected(self):
        r = self.c.post(reverse('api:courier-register'), {
            'full_name': 'X', 'phone': '+998936100002'}, format='json')
        self.assertEqual(r.status_code, 400)

    # ── Dashboard ──
    def test_dashboard_unregistered(self):
        u = make_user('+998936100011')
        c = APIClient(); c.force_authenticate(u)
        r = c.get(reverse('api:courier-dashboard'))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data['registered'])

    def test_dashboard_shows_available_and_stats(self):
        make_order(self.customer, status='ready')  # qabul mumkin
        make_order(self.customer, driver=self.driver, status='delivered', fee=15000,
                   delivered_at='2026-07-14T10:00:00Z')
        r = self.c.get(reverse('api:courier-dashboard'))
        self.assertTrue(r.data['registered'])
        self.assertEqual(len(r.data['available']), 1)
        self.assertEqual(r.data['stats']['delivered_count'], 1)
        self.assertEqual(r.data['stats']['earnings_total'], 15000)

    def test_pickup_orders_not_available(self):
        make_order(self.customer, status='ready', fulfillment_type='pickup')
        r = self.c.get(reverse('api:courier-dashboard'))
        self.assertEqual(len(r.data['available']), 0)

    # ── Bo'sh/band ──
    def test_toggle_available(self):
        r = self.c.post(reverse('api:courier-available'))
        self.assertFalse(r.data['is_available'])
        r = self.c.post(reverse('api:courier-available'))
        self.assertTrue(r.data['is_available'])

    # ── Qabul / voz kechish ──
    def test_accept_order(self):
        o = make_order(self.customer, status='ready')
        r = self.c.post(reverse('api:courier-accept', args=[o.id]))
        self.assertEqual(r.status_code, 200)
        o.refresh_from_db()
        self.assertEqual(o.status, 'assigned')
        self.assertEqual(o.driver_id, self.driver.id)

    def test_accept_when_busy_rejected(self):
        self.driver.is_available = False
        self.driver.save(update_fields=['is_available'])
        o = make_order(self.customer, status='ready')
        r = self.c.post(reverse('api:courier-accept', args=[o.id]))
        self.assertEqual(r.status_code, 400)

    def test_accept_already_taken_conflict(self):
        other = DeliveryDriver.objects.create(
            user=make_user('+998936100003'), full_name='B', phone='+998936100003')
        o = make_order(self.customer, driver=other, status='assigned')
        r = self.c.post(reverse('api:courier-accept', args=[o.id]))
        self.assertEqual(r.status_code, 409)

    def test_release_order(self):
        o = make_order(self.customer, driver=self.driver, status='assigned')
        r = self.c.post(reverse('api:courier-release', args=[o.id]))
        self.assertEqual(r.status_code, 200)
        o.refresh_from_db()
        self.assertEqual(o.status, 'ready')
        self.assertIsNone(o.driver_id)

    # ── Holat o'tishlari ──
    def test_status_flow(self):
        o = make_order(self.customer, driver=self.driver, status='assigned')
        for st in ('on_the_way', 'delivered'):
            r = self.c.post(reverse('api:courier-order-status', args=[o.id]),
                            {'status': st}, format='json')
            self.assertEqual(r.status_code, 200, f'{st}: {r.data}')
            o.refresh_from_db()
            self.assertEqual(o.status, st)
        self.assertIsNotNone(o.delivered_at)

    def test_status_invalid_transition(self):
        o = make_order(self.customer, driver=self.driver, status='assigned')
        r = self.c.post(reverse('api:courier-order-status', args=[o.id]),
                        {'status': 'delivered'}, format='json')
        # assigned -> delivered ORDER_TRANSITIONS'da yo'q
        self.assertEqual(r.status_code, 409)

    def test_status_not_own_order(self):
        o = make_order(self.customer, status='ready')  # driver yo'q
        r = self.c.post(reverse('api:courier-order-status', args=[o.id]),
                        {'status': 'on_the_way'}, format='json')
        self.assertEqual(r.status_code, 404)

    # ── Ruxsat ──
    def test_requires_auth(self):
        c = APIClient()
        r = c.get(reverse('api:courier-dashboard'))
        self.assertIn(r.status_code, (401, 403))
