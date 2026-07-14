"""Taksi haydovchi (taksist) mobil paneli API testlari."""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from main.models import User
from taxi.models import TaxiService, Taxist, Route, Trip


def make_user(phone):
    return User.objects.create_user(phone=phone, password='Test12345!', is_active=True)


class TaxistPanelTests(TestCase):
    def setUp(self):
        self.svc = TaxiService.objects.create(
            name='SamCity Taksi', short_number='1265', is_active=True)
        self.driver_user = make_user('+998936200001')
        self.taxist = Taxist.objects.create(
            user=self.driver_user, service=self.svc,
            full_name='Haydovchi', phone='+998936200001', is_active=True)
        self.c = APIClient()
        self.c.force_authenticate(self.driver_user)

    # ── Ro'yxatdan o'tish ──
    def test_register_creates_taxist_and_role(self):
        u = make_user('+998936200010')
        c = APIClient(); c.force_authenticate(u)
        r = c.post(reverse('api:taxist-register'), {
            'full_name': 'Yangi Haydovchi', 'phone': '+998936200010',
            'car_model': 'Chevrolet Cobalt'}, format='json')
        self.assertEqual(r.status_code, 201)
        u.refresh_from_db()
        self.assertEqual(u.role, 'driver')
        self.assertTrue(Taxist.objects.filter(user=u).exists())
        # Xizmat avtomatik biriktiriladi (web bilan bir xil)
        self.assertIsNotNone(Taxist.objects.get(user=u).service)

    def test_register_twice_rejected(self):
        r = self.c.post(reverse('api:taxist-register'), {
            'full_name': 'X', 'phone': '+998936200001'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_register_requires_name_and_phone(self):
        u = make_user('+998936200011')
        c = APIClient(); c.force_authenticate(u)
        r = c.post(reverse('api:taxist-register'), {'car_model': 'X'}, format='json')
        self.assertEqual(r.status_code, 400)

    # ── Dashboard (me) ──
    def test_me_unregistered(self):
        u = make_user('+998936200012')
        c = APIClient(); c.force_authenticate(u)
        r = c.get(reverse('api:taxist-me'))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data['registered'])

    def test_me_shows_routes_trips_and_stats(self):
        Route.objects.create(taxist=self.taxist, point_a='Shofirkon',
                             point_b='Buxoro', passenger_price=20000, is_active=True)
        passenger = make_user('+998936200013')
        Trip.objects.create(passenger=passenger, taxist=self.taxist,
                            point_a='A', point_b='B', price=20000, status='completed')
        Trip.objects.create(passenger=passenger, taxist=self.taxist,
                            point_a='A', point_b='B', price=25000, status='accepted')
        r = self.c.get(reverse('api:taxist-me'))
        self.assertTrue(r.data['registered'])
        self.assertEqual(len(r.data['routes']), 1)
        self.assertEqual(len(r.data['active']), 1)
        self.assertEqual(len(r.data['history']), 1)
        self.assertEqual(r.data['stats']['completed_count'], 1)
        self.assertEqual(r.data['stats']['active_count'], 1)
        self.assertEqual(r.data['stats']['earnings_total'], 20000)

    def test_me_shows_passenger_phone_to_driver(self):
        passenger = make_user('+998936200014')
        Trip.objects.create(passenger=passenger, taxist=self.taxist,
                            point_a='A', point_b='B', price=10000, status='accepted')
        r = self.c.get(reverse('api:taxist-me'))
        self.assertEqual(r.data['active'][0]['passenger_phone'], '+998936200014')

    # ── Profil tahriri ──
    def test_patch_profile(self):
        r = self.c.patch(reverse('api:taxist-me'),
                         {'car_model': 'Malibu', 'region': 'Buxoro'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.taxist.refresh_from_db()
        self.assertEqual(self.taxist.car_model, 'Malibu')
        self.assertEqual(self.taxist.region, 'Buxoro')

    def test_patch_without_profile_404(self):
        u = make_user('+998936200015')
        c = APIClient(); c.force_authenticate(u)
        r = c.patch(reverse('api:taxist-me'), {'car_model': 'X'}, format='json')
        self.assertEqual(r.status_code, 404)

    # ── Onlayn holati ──
    def test_toggle_online(self):
        self.assertFalse(self.taxist.is_online)
        r = self.c.post(reverse('api:taxist-online'))
        self.assertTrue(r.data['is_online'])
        r = self.c.post(reverse('api:taxist-online'))
        self.assertFalse(r.data['is_online'])

    def test_toggle_online_explicit(self):
        r = self.c.post(reverse('api:taxist-online'), {'is_online': True}, format='json')
        self.assertTrue(r.data['is_online'])
        self.taxist.refresh_from_db()
        self.assertTrue(self.taxist.is_online)

    # ── Marshrutlar ──
    def test_add_route(self):
        r = self.c.post(reverse('api:taxist-route-create'), {
            'point_a': 'Shofirkon', 'point_b': 'Buxoro',
            'passenger_price': 30000, 'delivery_price': 15000}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.taxist.routes.count(), 1)

    def test_add_route_requires_fields(self):
        r = self.c.post(reverse('api:taxist-route-create'),
                        {'point_a': 'A'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_add_route_without_profile_404(self):
        u = make_user('+998936200016')
        c = APIClient(); c.force_authenticate(u)
        r = c.post(reverse('api:taxist-route-create'), {
            'point_a': 'A', 'point_b': 'B', 'passenger_price': 10000}, format='json')
        self.assertEqual(r.status_code, 404)

    def test_delete_route(self):
        route = Route.objects.create(taxist=self.taxist, point_a='A', point_b='B',
                                     passenger_price=10000)
        r = self.c.delete(reverse('api:taxist-route-delete', args=[route.id]))
        self.assertEqual(r.status_code, 204)
        self.assertFalse(Route.objects.filter(pk=route.id).exists())

    def test_delete_others_route_404(self):
        other = Taxist.objects.create(full_name='Boshqa', phone='+998936200099')
        route = Route.objects.create(taxist=other, point_a='A', point_b='B',
                                     passenger_price=10000)
        r = self.c.delete(reverse('api:taxist-route-delete', args=[route.id]))
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Route.objects.filter(pk=route.id).exists())

    # ── Ruxsat ──
    def test_requires_auth(self):
        c = APIClient()
        r = c.get(reverse('api:taxist-me'))
        self.assertIn(r.status_code, (401, 403))
