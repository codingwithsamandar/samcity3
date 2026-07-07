"""Kuryer daromadi testlari — delivered_at belgilanishi va dashboard KPI'lari."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from main.models import User
from delivery.models import Order, DeliveryDriver


def make_user(phone):
    return User.objects.create_user(phone=phone, password='Test12345!', is_active=True)


def make_order(user, driver=None, status='ready', fee=10000, **extra):
    return Order.objects.create(
        user=user, full_name='Mijoz', phone='+998900000000',
        address='Test manzil', subtotal=50000, delivery_fee=fee,
        total=50000 + fee, status=status, driver=driver, **extra,
    )


class DriverEarningsTests(TestCase):
    def setUp(self):
        self.customer = make_user('+998936000001')
        self.driver_user = make_user('+998936000002')
        self.driver = DeliveryDriver.objects.create(
            user=self.driver_user, full_name='Kuryer', phone='+998936000002',
        )
        self.client.force_login(self.driver_user)

    def test_delivered_at_set_on_driver_delivered(self):
        order = make_order(self.customer, driver=self.driver, status='on_the_way')
        resp = self.client.post(
            reverse('delivery:driver_order_status', args=[order.id]),
            {'status': 'delivered'},
        )
        self.assertEqual(resp.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, 'delivered')
        self.assertIsNotNone(order.delivered_at)

    def test_delivered_at_not_set_on_other_status(self):
        order = make_order(self.customer, driver=self.driver, status='assigned')
        self.client.post(
            reverse('delivery:driver_order_status', args=[order.id]),
            {'status': 'picked_up'},
        )
        order.refresh_from_db()
        self.assertIsNone(order.delivered_at)

    def test_dashboard_period_earnings(self):
        now = timezone.now()
        # Bugungi yetkazma
        o1 = make_order(self.customer, driver=self.driver, status='delivered', fee=10000)
        Order.objects.filter(pk=o1.pk).update(delivered_at=now)
        # 3 kun oldingi yetkazma (haftaga kiradi, bugunga kirmaydi)
        o2 = make_order(self.customer, driver=self.driver, status='delivered', fee=8000)
        Order.objects.filter(pk=o2.pk).update(delivered_at=now - timedelta(days=3))
        # Eski yozuv — delivered_at yo'q (faqat jami summada)
        make_order(self.customer, driver=self.driver, status='delivered', fee=5000)

        resp = self.client.get(reverse('delivery:driver_dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['earnings_today'], 10000)
        self.assertEqual(resp.context['earnings_week'], 18000)
        self.assertEqual(resp.context['earnings'], 23000)
        self.assertEqual(resp.context['delivered_count'], 3)

    def test_confirm_pickup_sets_delivered_at(self):
        order = make_order(
            self.customer, status='ready',
            fulfillment_type='pickup', payment_status='paid', fee=0,
        )
        self.client.force_login(self.customer)
        resp = self.client.post(
            reverse('delivery:order_confirm_pickup', args=[order.id]),
        )
        self.assertEqual(resp.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, 'delivered')
        self.assertIsNotNone(order.delivered_at)
        self.assertIsNotNone(order.customer_confirmed_at)
