"""taxi bo'limi — taksist/marshrut topish + sayohat buyurtma."""

from unittest import skipUnless

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from .. import confirm, registry
from ..models import PendingAction
from . import _fixtures


def _mk_user(phone):
    return get_user_model().objects.create_user(phone=phone, password='x', name='T')


@skipUnless(settings.TAXI_ENABLED, "taksi arxivlangan (TAXI_ENABLED=False)")
class TaxiSetup(TestCase):
    def setUp(self):
        from taxi.models import Route, Taxist
        self.user = _mk_user('998920000001')
        self.taxist = Taxist.objects.create(full_name='Aziz Haydovchi', phone='998901112233',
                                            car_model='Nexia', is_active=True, is_online=True,
                                            trips_count=50)
        self.route = Route.objects.create(taxist=self.taxist, point_a='Shofirkon',
                                          point_b='Buxoro', passenger_price=40000)
        self.ctx = _fixtures.user_ctx(self.user, session_key='taxi')


@skipUnless(settings.TAXI_ENABLED, "taksi arxivlangan (TAXI_ENABLED=False)")
class FindTaxistsTests(TaxiSetup):
    def test_find_taxists(self):
        res = registry.dispatch('taxi', 'find_taxists', {}, self.ctx)
        self.assertEqual(res['ui']['type'], 'link_list')
        item = res['ui']['items'][0]
        self.assertEqual(item['title'], 'Aziz Haydovchi')
        self.assertEqual(item['phone'], '998901112233')

    def test_no_taxists(self):
        from taxi.models import Taxist
        Taxist.objects.update(is_active=False)
        res = registry.dispatch('taxi', 'find_taxists', {}, self.ctx)
        self.assertIsNone(res.get('ui'))


@skipUnless(settings.TAXI_ENABLED, "taksi arxivlangan (TAXI_ENABLED=False)")
class RoutesTests(TaxiSetup):
    def test_list_routes(self):
        res = registry.dispatch('taxi', 'list_routes', {'destination': 'buxoro'}, self.ctx)
        self.assertEqual(res['ui']['type'], 'card_list')
        self.assertIn('Shofirkon → Buxoro', [it['title'] for it in res['ui']['items']])

    def test_list_routes_all(self):
        res = registry.dispatch('taxi', 'list_routes', {}, self.ctx)
        self.assertTrue(res['ui']['items'])


@skipUnless(settings.TAXI_ENABLED, "taksi arxivlangan (TAXI_ENABLED=False)")
class ProposeTripTests(TaxiSetup):
    def test_propose_creates_pending_not_trip(self):
        from taxi.models import Trip
        res = registry.dispatch('taxi', 'propose_trip',
                                {'route_id': str(self.route.pk)}, self.ctx)
        self.assertEqual(res['result_status'], 'pending')
        self.assertEqual(res['ui']['type'], 'confirm_payment')
        self.assertEqual(res['ui']['total'], 40000)
        self.assertEqual(Trip.objects.count(), 0)

    def test_confirm_creates_trip(self):
        from taxi.models import Trip
        res = registry.dispatch('taxi', 'propose_trip',
                                {'route_id': f'route:{self.route.pk}'}, self.ctx)
        out = confirm.execute(res['pending_id'], self.user)
        self.assertTrue(out['ok'])
        self.assertEqual(Trip.objects.filter(passenger=self.user).count(), 1)
        trip = Trip.objects.get(passenger=self.user)
        self.assertEqual(trip.point_b, 'Buxoro')
        self.assertEqual(trip.price, 40000)
        self.assertEqual(trip.taxist, self.taxist)

    def test_double_confirm_one_trip(self):
        from taxi.models import Trip
        res = registry.dispatch('taxi', 'propose_trip',
                                {'route_id': str(self.route.pk)}, self.ctx)
        confirm.execute(res['pending_id'], self.user)
        confirm.execute(res['pending_id'], self.user)
        self.assertEqual(Trip.objects.filter(passenger=self.user).count(), 1)

    def test_anonymous_cannot_propose(self):
        res = registry.dispatch('taxi', 'propose_trip',
                                {'route_id': str(self.route.pk)}, _fixtures.anon_ctx())
        self.assertEqual(res['result_status'], 'denied')
        self.assertEqual(PendingAction.objects.count(), 0)
