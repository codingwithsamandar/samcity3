"""Taxi testlari — taksist ro'yxati, trip yaratish, egalik ruxsati."""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from main.models import User
from taxi.models import Taxist, Route, Trip


def make_user(phone):
    return User.objects.create_user(phone=phone, password='Test12345!', is_active=True)


class TaxiSetup(TestCase):
    def setUp(self):
        self.passenger = make_user('+998932000001')
        self.other = make_user('+998932000002')
        self.driver_user = make_user('+998932000003')
        self.taxist = Taxist.objects.create(
            user=self.driver_user, full_name='Akmal', phone='+998932000003')
        self.route = Route.objects.create(
            taxist=self.taxist, point_a='Samarqand', point_b='Toshkent',
            passenger_price=120000, delivery_price=60000)


class TaxistListTests(TaxiSetup):
    def test_taxist_list_public_read(self):
        # IsAuthenticatedOrReadOnly — anonim o'qiy oladi
        resp = APIClient().get(reverse('api:taxist-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('results', resp.data)


class TripTests(TaxiSetup):
    def _book(self, client):
        return client.post(reverse('api:trip-list'),
                           {'route_id': str(self.route.id), 'is_delivery': False},
                           format='json')

    def test_create_trip(self):
        c = APIClient()
        c.force_authenticate(self.passenger)
        resp = self._book(c)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['price'], 120000)
        self.assertEqual(Trip.objects.filter(passenger=self.passenger).count(), 1)

    def test_create_trip_requires_auth(self):
        resp = self._book(APIClient())
        self.assertIn(resp.status_code, (401, 403))

    def test_user_cannot_see_others_trip(self):
        c = APIClient()
        c.force_authenticate(self.passenger)
        self._book(c)
        trip = Trip.objects.filter(passenger=self.passenger).first()

        # Boshqa foydalanuvchi bu tripni ko'ra olmaydi (queryset egasi bo'yicha filtr)
        other = APIClient()
        other.force_authenticate(self.other)
        resp = other.get(reverse('api:trip-detail', args=[str(trip.id)]))
        self.assertEqual(resp.status_code, 404)

    def test_my_trips_only_own(self):
        c1 = APIClient(); c1.force_authenticate(self.passenger); self._book(c1)
        c2 = APIClient(); c2.force_authenticate(self.other)
        resp = c2.get(reverse('api:trip-list'))
        self.assertEqual(resp.status_code, 200)
        # other'da trip yo'q
        self.assertEqual(resp.data.get('count', 0), 0)
