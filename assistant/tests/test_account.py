"""account bo'limi + routing: profile/my_*/change_name va engine yo'naltirishi."""

from unittest import skipUnless

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from .. import confirm, engine, registry
from . import _fixtures


def _mk_user(phone, name='T'):
    return get_user_model().objects.create_user(phone=phone, password='x', name=name)


class AccountReadTests(TestCase):
    def setUp(self):
        self.user = _mk_user('998923000001', name='Ali')
        self.ctx = _fixtures.user_ctx(self.user, session_key='acc')

    def test_profile(self):
        res = registry.dispatch('account', 'profile', {}, self.ctx)
        self.assertEqual(res['ui']['type'], 'confirm')
        labels = {ln['value'] for ln in res['ui']['lines']}
        self.assertIn('Ali', labels)

    def test_my_orders_empty(self):
        res = registry.dispatch('account', 'my_orders', {}, self.ctx)
        self.assertIsNone(res.get('ui'))

    def test_my_orders(self):
        from delivery.models import Order
        Order.objects.create(user=self.user, full_name='Ali', phone='998900000000',
                             address='addr', subtotal=35000, delivery_fee=10000,
                             total=45000, status='pending')
        res = registry.dispatch('account', 'my_orders', {}, self.ctx)
        self.assertEqual(res['ui']['type'], 'link_list')
        self.assertIn('45 000', res['ui']['items'][0]['title'])

    def test_my_ads(self):
        from main.models import Ad
        Ad.objects.create(user=self.user, category='electronics', title='Telefon',
                          price=1000000, status='active')
        res = registry.dispatch('account', 'my_ads', {}, self.ctx)
        self.assertEqual(res['ui']['items'][0]['title'], 'Telefon')

    def test_my_bookings(self):
        import datetime as dt
        from booking.models import Venue, VenueService, VenueBooking
        owner = _mk_user('998923000009')
        v = Venue.objects.create(owner=owner, name='Zamon', venue_type='barber',
                                 is_active=True)
        svc = VenueService.objects.create(venue=v, name='Soch', price=30000,
                                          duration_minutes=30)
        VenueBooking.objects.create(venue=v, user=self.user, service=svc,
                                    booking_date=dt.date.today(),
                                    start_time=dt.time(11, 0), total_amount=30000,
                                    status='pending')
        res = registry.dispatch('account', 'my_bookings', {}, self.ctx)
        self.assertEqual(res['ui']['items'][0]['title'], 'Zamon')

    @skipUnless(settings.TAXI_ENABLED, "taksi arxivlangan (TAXI_ENABLED=False)")
    def test_my_trips(self):
        from taxi.models import Taxist, Trip
        tx = Taxist.objects.create(full_name='H', phone='998900000001',
                                   is_active=True)
        Trip.objects.create(passenger=self.user, taxist=tx, point_a='Shofirkon',
                            point_b='Buxoro', price=40000, status='accepted')
        res = registry.dispatch('account', 'my_trips', {}, self.ctx)
        self.assertIn('Buxoro', res['ui']['items'][0]['title'])

    def test_read_requires_auth(self):
        res = registry.dispatch('account', 'profile', {}, _fixtures.anon_ctx())
        self.assertEqual(res['result_status'], 'denied')


class ChangeNameTests(TestCase):
    def setUp(self):
        self.user = _mk_user('998923100001', name='Eski')
        self.ctx = _fixtures.user_ctx(self.user, session_key='cn')

    def test_change_name_flow(self):
        res = registry.dispatch('account', 'change_name', {'name': 'Samandar'}, self.ctx)
        self.assertEqual(res['result_status'], 'pending')
        self.assertEqual(res['ui']['type'], 'confirm')
        confirm.execute(res['pending_id'], self.user)
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, 'Samandar')

    def test_empty_name_rejected(self):
        res = registry.dispatch('account', 'change_name', {'name': '   '}, self.ctx)
        self.assertFalse(res['ok'])
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, 'Eski')

    def test_change_name_requires_auth(self):
        res = registry.dispatch('account', 'change_name', {'name': 'X'},
                                _fixtures.anon_ctx())
        self.assertEqual(res['result_status'], 'denied')


class AccountRoutingTests(TestCase):
    def test_account_query_detection(self):
        for p in ['buyurtmalarim', 'bronlarim', 'profilim',
                  'ismimni Samandarga o\'zgartir', "e'lonlarim"]:
            self.assertTrue(engine.is_account_query(p), p)

    def test_non_account(self):
        for p in ['taksi chaqir', 'salom', 'lavash yetkazib bering']:
            self.assertFalse(engine.is_account_query(p), p)


class DeliveryActionWordsTests(TestCase):
    """Arxitektor qo'shган delivery action so'zlari."""

    def test_delivery_is_action(self):
        for p in ['somsa yetkazib bering', 'lavash olib keling', 'suv olib kel']:
            self.assertTrue(engine.is_action_intent(p), p)

    def test_delivery_howto_not_action(self):
        self.assertFalse(engine.is_action_intent('yetkazib berish qanday ishlaydi'))
