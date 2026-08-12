"""delivery/booking to'ldirish — savatni ko'rish/tozalash, buyurtma/bron holati."""

import datetime as dt

from django.contrib.auth import get_user_model
from django.test import TestCase

from .. import confirm, registry
from . import _fixtures


def _mk_user(phone):
    return get_user_model().objects.create_user(phone=phone, password='x', name='T')


class DeliveryCartToolsTests(TestCase):
    def setUp(self):
        from delivery.models import CartItem, Product, Store, get_active_cart
        self.user = _mk_user('998921000001')
        owner = _mk_user('998921000002')
        store = Store.objects.create(owner=owner, name='Anor', store_type='delivery',
                                     is_active=True)
        self.p1 = Product.objects.create(store=store, name='Lavash', price=35000,
                                         stock=10, is_available=True)
        self.p2 = Product.objects.create(store=store, name="Ko'k choy", price=5000,
                                         stock=50, is_available=True)
        cart = get_active_cart(self.user)
        CartItem.objects.create(cart=cart, product=self.p1, quantity=2)
        CartItem.objects.create(cart=cart, product=self.p2, quantity=1)
        self.ctx = _fixtures.user_ctx(self.user, session_key='cartt')

    def test_view_cart(self):
        res = registry.dispatch('delivery', 'view_cart', {}, self.ctx)
        self.assertEqual(res['ui']['type'], 'link_list')
        self.assertEqual(len(res['ui']['items']), 2)
        self.assertIn('75 000', res['speech'])       # 70 000 + 5 000

    def test_view_empty_cart(self):
        from delivery.models import get_active_cart
        get_active_cart(self.user).items.all().delete()
        res = registry.dispatch('delivery', 'view_cart', {}, self.ctx)
        self.assertIsNone(res.get('ui'))
        self.assertIn("bo'sh", res['speech'].lower())

    def test_remove_from_cart(self):
        from delivery.models import get_active_cart
        res = registry.dispatch('delivery', 'remove_from_cart',
                                {'product_id': self.p1.pk}, self.ctx)
        self.assertTrue(res['ok'])
        self.assertEqual(get_active_cart(self.user).items.count(), 1)

    def test_remove_missing(self):
        res = registry.dispatch('delivery', 'remove_from_cart',
                                {'product_id': 999999}, self.ctx)
        self.assertFalse(res['ok'])

    def test_my_orders(self):
        from delivery.models import Order
        Order.objects.create(user=self.user, full_name='T', phone='998900000000',
                             address='addr', subtotal=35000, delivery_fee=10000,
                             total=45000, status='pending')
        res = registry.dispatch('delivery', 'my_orders', {}, self.ctx)
        self.assertEqual(res['ui']['type'], 'link_list')
        self.assertIn('45 000', res['ui']['items'][0]['title'])

    def test_no_orders(self):
        res = registry.dispatch('delivery', 'my_orders', {}, self.ctx)
        self.assertIsNone(res.get('ui'))

    def test_cart_tools_require_auth(self):
        res = registry.dispatch('delivery', 'view_cart', {}, _fixtures.anon_ctx())
        self.assertEqual(res['result_status'], 'denied')


class BookingManageTests(TestCase):
    def setUp(self):
        from booking.models import Venue, VenueService, VenueBooking
        self.user = _mk_user('998921100001')
        self.other = _mk_user('998921100002')
        owner = _mk_user('998921100003')
        self.venue = Venue.objects.create(owner=owner, name='Zamon', venue_type='barber',
                                          is_active=True, working_hours_start=dt.time(9, 0),
                                          working_hours_end=dt.time(20, 0))
        self.svc = VenueService.objects.create(venue=self.venue, name='Soch olish',
                                               price=30000, duration_minutes=30)
        self.booking = VenueBooking.objects.create(
            venue=self.venue, user=self.user, service=self.svc,
            booking_date=dt.date.today(), start_time=dt.time(11, 0),
            total_amount=30000, status='pending')
        self.ctx = _fixtures.user_ctx(self.user, session_key='mybk')

    def test_my_bookings(self):
        res = registry.dispatch('booking', 'my_bookings', {}, self.ctx)
        self.assertEqual(res['ui']['type'], 'card_list')
        self.assertIn('Zamon', res['ui']['items'][0]['title'])

    def test_cancel_flow(self):
        from booking.models import VenueBooking
        res = registry.dispatch('booking', 'cancel_booking',
                                {'booking_id': str(self.booking.pk)}, self.ctx)
        self.assertEqual(res['result_status'], 'pending')
        self.assertEqual(res['ui']['type'], 'confirm')
        confirm.execute(res['pending_id'], self.user)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'cancelled')

    def test_cancel_prefixed_id(self):
        res = registry.dispatch('booking', 'cancel_booking',
                                {'booking_id': f'booking:{self.booking.pk}'}, self.ctx)
        self.assertEqual(res['result_status'], 'pending')

    def test_cannot_cancel_others_booking(self):
        """Egalik: boshqa odamning broni → denied (guard owns)."""
        res = registry.dispatch('booking', 'cancel_booking',
                                {'booking_id': str(self.booking.pk)},
                                _fixtures.user_ctx(self.other, session_key='o'))
        self.assertEqual(res['result_status'], 'denied')

    def test_no_bookings(self):
        res = registry.dispatch('booking', 'my_bookings', {},
                                _fixtures.user_ctx(self.other, session_key='o2'))
        self.assertIsNone(res.get('ui'))
