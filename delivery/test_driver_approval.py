"""Kuryer bo'lish uchun admin tasdig'i — testlar.

    python manage.py test delivery.test_driver_approval
"""
from django.test import TestCase
from django.urls import reverse

from main.models import User
from delivery.models import DeliveryDriver


def make_user(phone, **kw):
    return User.objects.create_user(phone=phone, password='x', is_active=True, **kw)


class DriverApprovalTests(TestCase):
    def setUp(self):
        self.user = make_user('+998910000501')
        self.admin = make_user('+998910000502', is_staff=True, is_superuser=True)

    def _apply(self):
        self.client.force_login(self.user)
        return self.client.post(reverse('delivery:driver_register'), {
            'full_name': 'Ali Valiyev', 'phone': '901234567',
            'vehicle_type': 'moto', 'vehicle_number': '01A123BC',
        }, follow=True)

    # ── Ariza yuborish ──────────────────────────────────────────────────────
    def test_application_starts_pending(self):
        self._apply()
        d = DeliveryDriver.objects.get(user=self.user)
        self.assertEqual(d.status, DeliveryDriver.STATUS_PENDING)
        self.assertFalse(d.is_approved)
        self.assertFalse(d.can_work)

    def test_role_not_granted_on_application(self):
        """Eng muhimi: ariza yuborish bilan 'driver' roli BERILMAYDI."""
        self._apply()
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, 'user')

    def test_applicant_sees_pending_page_not_dashboard(self):
        self._apply()
        resp = self.client.get(reverse('delivery:driver_dashboard'))
        self.assertContains(resp, "ko'rib chiqilmoqda")
        self.assertNotContains(resp, 'Qabul qilish')

    def test_pending_driver_gets_no_orders_feed(self):
        self._apply()
        resp = self.client.get(reverse('delivery:driver_orders_feed'))
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()['error'], 'not_approved')

    # ── Tasdiqlash ──────────────────────────────────────────────────────────
    def test_approve_grants_role_and_access(self):
        self._apply()
        d = DeliveryDriver.objects.get(user=self.user)
        d.approve(by=self.admin)

        d.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(d.status, DeliveryDriver.STATUS_APPROVED)
        self.assertTrue(d.can_work)
        self.assertEqual(d.reviewed_by, self.admin)
        self.assertIsNotNone(d.reviewed_at)
        self.assertEqual(self.user.role, 'driver')

    def test_approved_driver_reaches_dashboard(self):
        self._apply()
        DeliveryDriver.objects.get(user=self.user).approve(by=self.admin)
        resp = self.client.get(reverse('delivery:driver_dashboard'))
        self.assertNotContains(resp, "ko'rib chiqilmoqda")

    def test_approved_driver_feed_works(self):
        self._apply()
        DeliveryDriver.objects.get(user=self.user).approve(by=self.admin)
        resp = self.client.get(reverse('delivery:driver_orders_feed'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['ok'])

    # ── Rad etish ───────────────────────────────────────────────────────────
    def test_reject_blocks_and_strips_role(self):
        self._apply()
        d = DeliveryDriver.objects.get(user=self.user)
        d.approve(by=self.admin)          # avval tasdiqlandi (rol berildi)
        d.reject(by=self.admin, reason='Hujjatlar yetarli emas')

        d.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(d.status, DeliveryDriver.STATUS_REJECTED)
        self.assertFalse(d.can_work)
        self.assertEqual(self.user.role, 'user')
        self.assertEqual(d.reject_reason, 'Hujjatlar yetarli emas')

    def test_rejected_sees_reason(self):
        self._apply()
        d = DeliveryDriver.objects.get(user=self.user)
        d.reject(by=self.admin, reason='Yoshi mos emas')
        resp = self.client.get(reverse('delivery:driver_dashboard'))
        self.assertContains(resp, 'rad etildi')
        self.assertContains(resp, 'Yoshi mos emas')

    # ── Buyurtma qabul qilish darvozasi ────────────────────────────────────
    def test_pending_cannot_accept_orders(self):
        from delivery.models import Order
        self._apply()
        order = Order.objects.create(
            user=self.admin, full_name='Mijoz', phone='+998901112233',
            address="Navoiy ko'chasi 1", status='ready')
        resp = self.client.post(
            reverse('delivery:order_accept', args=[order.id]), follow=True)
        order.refresh_from_db()
        self.assertIsNone(order.driver)
        self.assertContains(resp, 'tasdiqlanmagan')

    # ── Bloklangan tasdiqlangan kuryer ham ishlay olmaydi ──────────────────
    def test_approved_but_blocked_cannot_work(self):
        self._apply()
        d = DeliveryDriver.objects.get(user=self.user)
        d.approve(by=self.admin)
        d.is_active = False
        d.save(update_fields=['is_active'])
        d.refresh_from_db()
        self.assertTrue(d.is_approved)
        self.assertFalse(d.can_work)
