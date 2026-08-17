"""Kuryer oqimi: mahsulotni olmasdan yo'lga chiqa olmaydi + naqd to'lov ogohligi.

Ikki qoida:
1. `assigned → on_the_way` YOPIQ. Kuryer avval «do'kondan oldim» (picked_up)
   deb belgilashi shart, aks holda mijoz bo'sh qo'l bilan kelayotgan kuryerni
   kutardi.
2. Naqd buyurtmada kuryer qancha pul olishini oldindan ko'radi.
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from main.models import User
from delivery.models import (
    Store, Product, Order, OrderItem, DeliveryDriver, can_transition,
)


def make_user(phone):
    return User.objects.create_user(phone=phone, password='Test12345!', is_active=True)


class PickupBeforeRoadTests(TestCase):
    def setUp(self):
        self.owner = make_user('+998936000001')
        self.customer = make_user('+998936000002')
        self.driver_user = make_user('+998936000003')
        self.store = Store.objects.create(owner=self.owner, name="Do'kon")
        self.product = Product.objects.create(
            store=self.store, name='Non', price=Decimal('5000'), stock=10,
            is_available=True)
        self.driver = DeliveryDriver.objects.create(
            user=self.driver_user, full_name='Kuryer', phone='+998936000003',
            is_available=True, status='approved')
        self.order = Order.objects.create(
            user=self.customer, address='Shofirkon, 1-uy', status='assigned',
            driver=self.driver, total=60000, payment_method='cash',
            payment_status='unpaid')
        OrderItem.objects.create(
            order=self.order, product=self.product, product_name='Non',
            store_name=self.store.name, price=Decimal('5000'), quantity=1)

    # ── Qoida darajasida ────────────────────────────────────────────────────
    def test_transition_table_blocks_road_before_pickup(self):
        self.assertFalse(can_transition('assigned', 'on_the_way'))
        self.assertTrue(can_transition('assigned', 'picked_up'))
        self.assertTrue(can_transition('picked_up', 'on_the_way'))

    def test_courier_can_still_release_or_cancel(self):
        self.assertTrue(can_transition('assigned', 'ready'))
        self.assertTrue(can_transition('assigned', 'cancelled'))

    # ── Veb panel ───────────────────────────────────────────────────────────
    def _post_status(self, new):
        self.client.force_login(self.driver_user)
        return self.client.post(
            reverse('delivery:driver_order_status', args=[self.order.id]),
            {'status': new}, follow=True)

    def test_web_rejects_on_the_way_from_assigned(self):
        self._post_status('on_the_way')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'assigned')

    def test_web_full_sequence(self):
        self._post_status('picked_up')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'picked_up')
        self._post_status('on_the_way')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'on_the_way')
        self._post_status('delivered')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'delivered')

    def test_dashboard_shows_pickup_button_not_road(self):
        self.client.force_login(self.driver_user)
        resp = self.client.get(reverse('delivery:driver_dashboard'))
        # Shablondagi oddiy matn escape qilinmaydi — apostrof o'z holicha.
        self.assertContains(resp, "Mahsulotni do'kondan oldim")
        self.assertNotContains(resp, "Yo'lga chiqdim")

    # ── Mobil API ───────────────────────────────────────────────────────────
    def test_api_rejects_on_the_way_from_assigned(self):
        self.client.force_login(self.driver_user)
        resp = self.client.post(
            reverse('api:courier-order-status', args=[self.order.id]),
            {'status': 'on_the_way'}, content_type='application/json')
        self.assertEqual(resp.status_code, 409)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'assigned')


class CashVisibilityTests(TestCase):
    def setUp(self):
        self.owner = make_user('+998936000010')
        self.customer = make_user('+998936000011')
        self.driver_user = make_user('+998936000012')
        self.store = Store.objects.create(owner=self.owner, name="Do'kon")
        self.driver = DeliveryDriver.objects.create(
            user=self.driver_user, full_name='Kuryer', phone='+998936000012',
            is_available=True, status='approved')

    def _order(self, method, pay_status, status='ready', driver=None):
        return Order.objects.create(
            user=self.customer, address='Shofirkon, 2-uy', status=status,
            driver=driver, total=60000, delivery_fee=10000,
            fulfillment_type='delivery',
            payment_method=method, payment_status=pay_status)

    # ── Qoida ───────────────────────────────────────────────────────────────
    def test_cash_to_collect_only_for_unpaid_cash(self):
        self.assertEqual(self._order('cash', 'unpaid').cash_to_collect, 60000)
        self.assertEqual(self._order('card', 'paid').cash_to_collect, 0)
        # Naqd bo'lsa ham, allaqachon to'langan bo'lsa pul so'ralmaydi.
        self.assertEqual(self._order('cash', 'paid').cash_to_collect, 0)

    # ── Panel: qabul qilishdan OLDIN ham ko'rinadi ──────────────────────────
    def test_available_list_warns_about_cash(self):
        self._order('cash', 'unpaid')
        self.client.force_login(self.driver_user)
        resp = self.client.get(reverse('delivery:driver_dashboard'))
        self.assertContains(resp, 'NAQD OLINADI')
        self.assertContains(resp, '60 000')

    def test_available_list_marks_paid_order(self):
        self._order('card', 'paid')
        self.client.force_login(self.driver_user)
        resp = self.client.get(reverse('delivery:driver_dashboard'))
        self.assertContains(resp, "To'langan")
        self.assertNotContains(resp, 'NAQD OLINADI')

    def test_active_order_card_shows_cash(self):
        self._order('cash', 'unpaid', status='assigned', driver=self.driver)
        self.client.force_login(self.driver_user)
        resp = self.client.get(reverse('delivery:driver_dashboard'))
        self.assertContains(resp, 'NAQD OLINADI')

    # ── Mobil API ───────────────────────────────────────────────────────────
    def test_api_exposes_cash_to_collect(self):
        self._order('cash', 'unpaid', status='assigned', driver=self.driver)
        self.client.force_login(self.driver_user)
        resp = self.client.get(reverse('api:courier-dashboard'))
        self.assertEqual(resp.status_code, 200)
        active = resp.json()['active']
        self.assertEqual(active[0]['cash_to_collect'], 60000)
