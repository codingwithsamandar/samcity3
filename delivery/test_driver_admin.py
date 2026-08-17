"""Admin panelidan kuryer qo'shish va olib tashlash.

Asosiy xavf — o'chirish: `Order.driver` SET_NULL, ya'ni qo'lida buyurtma
turgan kuryer o'chirilsa buyurtma hech kimsiz «assigned» holatida qotib
qolardi. Shuning uchun bunday o'chirish to'xtatiladi.
"""
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.test import TestCase, RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage

from main.models import User
from delivery.admin import DeliveryDriverAdmin, DeliveryDriverForm
from delivery.models import DeliveryDriver, Order, Store, Product


def make_user(phone, **extra):
    return User.objects.create_user(phone=phone, password='Test12345!',
                                    is_active=True, **extra)


def _request(user):
    req = RequestFactory().post('/admin/')
    req.user = user
    req.session = {}
    req._messages = FallbackStorage(req)
    return req


class DriverAdminTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = DeliveryDriverAdmin(DeliveryDriver, self.site)
        self.staff = make_user('+998934000001', is_staff=True, is_superuser=True)
        self.person = make_user('+998934000002', name='Yangi Kuryer')
        self.req = _request(self.staff)

    def _messages(self):
        return [str(m) for m in self.req._messages]

    # ── Qo'shish ────────────────────────────────────────────────────────────
    def test_form_fills_name_and_phone_from_user(self):
        form = DeliveryDriverForm(data={
            'user': self.person.pk, 'vehicle_type': 'moto',
            'full_name': '', 'phone': '', 'vehicle_number': '',
            'is_active': True, 'is_available': True,
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['full_name'], 'Yangi Kuryer')
        self.assertEqual(form.cleaned_data['phone'], self.person.phone)

    def test_adding_driver_sets_role_and_notifies(self):
        driver = DeliveryDriver(user=self.person, full_name='Yangi Kuryer',
                                phone=self.person.phone)
        self.admin.save_model(self.req, driver, None, change=False)
        self.person.refresh_from_db()
        self.assertEqual(self.person.role, 'driver')
        self.assertEqual(
            self.person.notifications.filter(text__icontains='kuryerlik').count(), 1)

    def test_adding_driver_keeps_business_role(self):
        """Do'kon egasi ham kuryer bo'lishi mumkin — roli bosib ketilmaydi."""
        self.person.role = 'business'
        self.person.save(update_fields=['role'])
        driver = DeliveryDriver(user=self.person, full_name='X', phone='+998934000002')
        self.admin.save_model(self.req, driver, None, change=False)
        self.person.refresh_from_db()
        self.assertEqual(self.person.role, 'business')

    # ── Olib tashlash ───────────────────────────────────────────────────────
    def _driver_with_order(self, status):
        driver = DeliveryDriver.objects.create(
            user=self.person, full_name='Kuryer', phone='+998934000002', status='approved')
        customer = make_user('+998934000003')
        Order.objects.create(user=customer, address='Shofirkon, 1-uy',
                             status=status, driver=driver, total=10000)
        return driver

    def test_delete_blocked_while_order_in_hand(self):
        driver = self._driver_with_order('on_the_way')
        self.admin.delete_model(self.req, driver)
        self.assertTrue(DeliveryDriver.objects.filter(pk=driver.pk).exists())
        self.assertIn("tugallanmagan buyurtma", ' '.join(self._messages()))

    def test_delete_allowed_after_orders_finished(self):
        driver = self._driver_with_order('delivered')
        self.person.role = 'driver'
        self.person.save(update_fields=['role'])
        self.admin.delete_model(self.req, driver)
        self.assertFalse(DeliveryDriver.objects.filter(pk=driver.pk).exists())
        self.person.refresh_from_db()
        self.assertEqual(self.person.role, 'user')          # rol qaytarildi
        self.assertTrue(Order.objects.filter(driver__isnull=True).exists())  # tarix qoldi

    def test_bulk_delete_blocked_by_one_active_order(self):
        busy = self._driver_with_order('assigned')
        other_user = make_user('+998934000004')
        free = DeliveryDriver.objects.create(
            user=other_user, full_name='Bo\'sh', phone='+998934000004', status='approved')
        self.admin.delete_queryset(
            self.req, DeliveryDriver.objects.filter(pk__in=[busy.pk, free.pk]))
        self.assertEqual(DeliveryDriver.objects.count(), 2)

    # ── Bloklash ────────────────────────────────────────────────────────────
    def test_block_action_stops_new_orders(self):
        driver = DeliveryDriver.objects.create(
            user=self.person, full_name='Kuryer', phone='+998934000002',
            is_active=True, is_available=True, status='approved')
        self.admin.block_drivers(self.req, DeliveryDriver.objects.filter(pk=driver.pk))
        driver.refresh_from_db()
        self.assertFalse(driver.is_active)
        self.assertFalse(driver.is_available)

    def test_active_orders_column(self):
        driver = self._driver_with_order('picked_up')
        self.assertEqual(self.admin.active_orders(driver), '1 ta')
