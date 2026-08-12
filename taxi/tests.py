"""Taxi testlari — taksist ro'yxati, trip yaratish, egalik ruxsati."""
from unittest import skipUnless

from django.conf import settings
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


@skipUnless(settings.TAXI_ENABLED, "taksi arxivlangan (TAXI_ENABLED=False)")
class TaxistListTests(TaxiSetup):
    def test_taxist_list_public_read(self):
        # IsAuthenticatedOrReadOnly — anonim o'qiy oladi
        resp = APIClient().get(reverse('api:taxist-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('results', resp.data)


@skipUnless(settings.TAXI_ENABLED, "taksi arxivlangan (TAXI_ENABLED=False)")
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


class TaxiServiceModelTests(TestCase):
    """Dispetcher xizmati — narx kalkulyatori va sharh/baho mantiqlari."""

    def setUp(self):
        from taxi.models import TaxiService
        self.u1 = make_user('+998932000010')
        self.u2 = make_user('+998932000011')
        self.service = TaxiService.objects.create(
            name='Shofirkon Taxi', short_number='1265',
            base_price=5000, price_per_km=2000,
        )

    def test_example_price(self):
        # 5 km: 5000 + 2000*5 = 15000
        self.assertEqual(self.service.example_price(5), 15000)
        self.assertEqual(self.service.example_5km, 15000)
        self.assertEqual(self.service.example_price(0), 5000)

    def test_avg_rating_and_count(self):
        from taxi.models import ServiceReview
        self.assertEqual(self.service.avg_rating, 0)
        ServiceReview.objects.create(service=self.service, user=self.u1, rating=5)
        ServiceReview.objects.create(service=self.service, user=self.u2, rating=4)
        self.assertEqual(self.service.avg_rating, 4.5)
        self.assertEqual(self.service.review_count, 2)

    def test_one_review_per_user(self):
        from django.db import IntegrityError
        from taxi.models import ServiceReview
        ServiceReview.objects.create(service=self.service, user=self.u1, rating=5)
        with self.assertRaises(IntegrityError):
            ServiceReview.objects.create(service=self.service, user=self.u1, rating=1)
