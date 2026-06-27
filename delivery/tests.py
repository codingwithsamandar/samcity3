"""Delivery testlari — buyurtma holat o'tishi, haydovchi, egalik ruxsati."""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from main.models import User
from delivery.models import (
    Store, Product, DeliveryDriver, Order, can_transition, ORDER_TRANSITIONS,
)


def make_user(phone):
    return User.objects.create_user(phone=phone, password='Test12345!', is_active=True)


class OrderAcceptRaceTests(TestCase):
    """Ikki haydovchi bitta 'ready' buyurtmani ola olmasligi (race-himoya)."""

    def setUp(self):
        self.customer = make_user('+998931000050')
        self.u1 = make_user('+998931000051')
        self.u2 = make_user('+998931000052')
        self.d1 = DeliveryDriver.objects.create(
            user=self.u1, full_name='D1', phone='+998931000051', is_available=True)
        self.d2 = DeliveryDriver.objects.create(
            user=self.u2, full_name='D2', phone='+998931000052', is_available=True)
        self.order = Order.objects.create(
            user=self.customer, address='Shofirkon, 1-uy', status='ready', total=20000)

    def test_second_driver_cannot_take_assigned_order(self):
        # 1-haydovchi qabul qiladi
        self.client.force_login(self.u1)
        self.client.post(reverse('delivery:order_accept', args=[self.order.id]))
        self.order.refresh_from_db()
        self.assertEqual(self.order.driver_id, self.d1.id)
        self.assertEqual(self.order.status, 'assigned')

        # 2-haydovchi o'sha buyurtmani olishga urinadi — o'zgartira olmaydi
        self.client.force_login(self.u2)
        self.client.post(reverse('delivery:order_accept', args=[self.order.id]))
        self.order.refresh_from_db()
        self.assertEqual(self.order.driver_id, self.d1.id)  # hali ham 1-haydovchida


class CanTransitionTests(TestCase):
    """Buyurtma holat o'tishi validatsiyasi (can_transition)."""

    def test_valid_forward_transitions(self):
        self.assertTrue(can_transition('pending', 'accepted'))
        self.assertTrue(can_transition('accepted', 'preparing'))
        self.assertTrue(can_transition('preparing', 'ready'))
        self.assertTrue(can_transition('ready', 'assigned'))
        self.assertTrue(can_transition('on_the_way', 'delivered'))

    def test_invalid_transitions_blocked(self):
        # Bosqichni o'tkazib yuborib bo'lmaydi
        self.assertFalse(can_transition('pending', 'delivered'))
        self.assertFalse(can_transition('pending', 'ready'))
        # Yakunlangan/bekor qilingandan keyin o'zgartirib bo'lmaydi
        self.assertFalse(can_transition('delivered', 'pending'))
        self.assertFalse(can_transition('cancelled', 'accepted'))

    def test_cancellable_from_active_states(self):
        for st in ('pending', 'accepted', 'preparing', 'ready', 'on_the_way'):
            self.assertIn('cancelled', ORDER_TRANSITIONS.get(st, set()))


class DeliveryDriverTests(TestCase):
    def test_create_driver_defaults(self):
        u = make_user('+998931000001')
        d = DeliveryDriver.objects.create(
            user=u, full_name='Ali', phone='+998931000001', vehicle_type='moto')
        self.assertTrue(d.is_available)
        self.assertTrue(d.is_active)


class StoreOwnerPermissionTests(TestCase):
    """Faqat egasi do'konini tahrirlay/o'chira oladi (web view)."""

    def setUp(self):
        self.owner = make_user('+998931000002')
        self.other = make_user('+998931000003')
        self.store = Store.objects.create(owner=self.owner, name='Mening do\'konim')

    def test_non_owner_cannot_edit_store(self):
        self.client.force_login(self.other)
        resp = self.client.post(
            reverse('delivery:store_edit', args=[self.store.pk]),
            {'name': 'O\'zgartirilgan'})
        # Egasi bo'lmagan → tahrir qo'llanmaydi (redirect)
        self.assertEqual(resp.status_code, 302)
        self.store.refresh_from_db()
        self.assertEqual(self.store.name, 'Mening do\'konim')

    def test_non_owner_cannot_delete_store(self):
        self.client.force_login(self.other)
        resp = self.client.post(reverse('delivery:store_delete', args=[self.store.pk]))
        self.assertIn(resp.status_code, (302, 403, 404))
        self.assertTrue(Store.objects.filter(pk=self.store.pk).exists())

    def test_owner_can_add_product_via_api(self):
        from rest_framework.test import APIClient
        api = APIClient()
        api.force_authenticate(self.owner)
        resp = api.post(reverse('api:store-products', args=[self.store.pk]),
                        {'name': 'Non', 'price': 3000, 'stock': 10}, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Product.objects.filter(store=self.store).count(), 1)

    def test_non_owner_cannot_add_product_via_api(self):
        from rest_framework.test import APIClient
        api = APIClient()
        api.force_authenticate(self.other)
        resp = api.post(reverse('api:store-products', args=[self.store.pk]),
                        {'name': 'Non', 'price': 3000}, format='json')
        self.assertEqual(resp.status_code, 404)  # do'kon topilmadi (boshqaning)
        self.assertEqual(Product.objects.filter(store=self.store).count(), 0)
