"""GET /api/me/ — qobiliyat belgilari testi.

`role` bitta qiymat oladi, lekin bitta odam bir vaqtda kuryer HAM, do'kon egasi
HAM bo'lishi mumkin. Mobil ilova qaysi panelni ko'rsatishni shu belgilarga qarab
hal qiladi — shu sabab ular to'g'ri qaytishi kritik."""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from main.models import User
from delivery.models import DeliveryDriver, Store
from taxi.models import Taxist
from booking.models import Venue


def make_user(phone):
    return User.objects.create_user(phone=phone, password='Test12345!', is_active=True)


class CapabilityFlagsTests(TestCase):
    def _me(self, user):
        c = APIClient()
        c.force_authenticate(user)
        return c.get(reverse('api:me'))

    def test_plain_user_has_no_capabilities(self):
        r = self._me(make_user('+998900000001'))
        self.assertEqual(r.status_code, 200)
        for f in ('is_courier', 'is_taxist', 'is_store_owner', 'is_venue_owner'):
            self.assertFalse(r.data[f], f)

    def test_courier_flag(self):
        u = make_user('+998900000002')
        DeliveryDriver.objects.create(user=u, full_name='K', phone='+998900000002', status='approved')
        r = self._me(u)
        self.assertTrue(r.data['is_courier'])
        self.assertFalse(r.data['is_taxist'])

    def test_store_owner_flag(self):
        u = make_user('+998900000003')
        Store.objects.create(owner=u, name='Do\'kon', store_type='delivery')
        r = self._me(u)
        self.assertTrue(r.data['is_store_owner'])
        self.assertFalse(r.data['is_venue_owner'])

    def test_venue_owner_flag(self):
        u = make_user('+998900000004')
        Venue.objects.create(owner=u, name='Zal')
        r = self._me(u)
        self.assertTrue(r.data['is_venue_owner'])

    def test_multi_role_courier_and_store_owner(self):
        """Kuryer keyin do'kon ochsa — IKKALA belgi ham True bo'lishi kerak."""
        u = make_user('+998900000005')
        DeliveryDriver.objects.create(user=u, full_name='K', phone='+998900000005', status='approved')
        Store.objects.create(owner=u, name='Do\'kon', store_type='delivery')
        r = self._me(u)
        self.assertTrue(r.data['is_courier'])
        self.assertTrue(r.data['is_store_owner'])
