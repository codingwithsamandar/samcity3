"""To'yxona (wedding) — KUNLIK bron: sana + mehmon soni, sig'im tekshiruvi.

Slot oqimидан (barber/salon) farqi: xizmat/usta yo'q, butun kun egallanadi,
narx `Venue.price_per_day`.
"""

import datetime as dt

from django.contrib.auth import get_user_model
from django.test import TestCase

from .. import confirm, registry
from . import _fixtures


def _mk_user(phone):
    return get_user_model().objects.create_user(phone=phone, password='x', name='T')


class WeddingRoutingTests(TestCase):
    """«to'yxona kerak» bron amali — agentga; «to'yxona qayerda» — bepul places."""

    def test_wedding_need_retreats_to_agent(self):
        from .. import engine
        for p in ["to'yxona kerak", "to'yxona kerak, 200 kishi",
                  "to'yxona bron qil", 'zal kerak 200 kishi']:
            self.assertEqual(engine.handle(p)['intent'], 'unknown', p)

    def test_wedding_where_stays_places(self):
        from .. import engine
        # Manzil so'rovi — bepul places branch'ida qolsin (agentga ketmasin)
        self.assertNotEqual(engine.handle("to'yxona qayerda")['intent'], 'unknown')
        self.assertFalse(engine.is_action_intent("to'yxona qayerda"))

    def test_wedding_howto_stays_kb(self):
        from .. import engine
        self.assertFalse(engine.is_action_intent('qanday toyxona bron qilaman'))


class WeddingBookingTests(TestCase):
    def setUp(self):
        from booking.models import Venue
        self.user = _mk_user('998926000001')
        owner = _mk_user('998926000002')
        self.hall = Venue.objects.create(
            owner=owner, name="Navro'z To'yxonasi", venue_type='wedding',
            is_active=True, capacity=300, price_per_day=12000000,
            prepay_required=False,   # ⚠️ model standarti True — seed ham False qo'yadi
            working_hours_start=dt.time(8, 0), working_hours_end=dt.time(23, 0))
        self.ctx = _fixtures.user_ctx(self.user, session_key='wed')

    def test_find_wedding_venue(self):
        res = registry.dispatch('booking', 'find_venue',
                                {'venue_type': 'wedding'}, self.ctx)
        self.assertEqual(res['ui']['type'], 'card_list')
        item = res['ui']['items'][0]
        self.assertEqual(item['title'], "Navro'z To'yxonasi")
        self.assertIn('300 kishilik', item['subtitle'])
        # Bitta variant → keyingi qadam sana/kishi soni (xizmat EMAS)
        self.assertIn('kun', res['speech'].lower())

    def test_propose_and_place(self):
        from booking.models import VenueBooking
        res = registry.dispatch('booking', 'propose_wedding',
                                {'venue_id': str(self.hall.pk), 'day': 'ertaga',
                                 'guests': 200}, self.ctx)
        self.assertEqual(res['result_status'], 'pending')
        confirm.execute(res['pending_id'], self.user)
        b = VenueBooking.objects.get(venue=self.hall, user=self.user)
        self.assertEqual(b.guests, 200)
        self.assertIsNone(b.start_time)          # kunlik — vaqt yo'q
        self.assertIsNone(b.service_id)
        self.assertEqual(b.total_amount, 12000000)

    def test_capacity_exceeded(self):
        res = registry.dispatch('booking', 'propose_wedding',
                                {'venue_id': str(self.hall.pk), 'day': 'ertaga',
                                 'guests': 500}, self.ctx)
        self.assertFalse(res['ok'])
        self.assertIn("sig'", res['speech'])

    def test_day_already_taken(self):
        from booking.models import VenueBooking
        VenueBooking.objects.create(venue=self.hall, user=self.user,
                                    booking_date=dt.date.today() + dt.timedelta(days=1),
                                    guests=100, total_amount=0, status='confirmed')
        res = registry.dispatch('booking', 'propose_wedding',
                                {'venue_id': str(self.hall.pk), 'day': 'ertaga',
                                 'guests': 100}, self.ctx)
        self.assertFalse(res['ok'])
        self.assertIn('band', res['speech'])

    def test_slot_venue_rejected(self):
        """Sartaroshxonaga kunlik bron qo'llanilmasin."""
        from booking.models import Venue
        barber = Venue.objects.create(owner=self.user, name='Zamon',
                                      venue_type='barber', is_active=True)
        res = registry.dispatch('booking', 'propose_wedding',
                                {'venue_id': str(barber.pk), 'day': 'ertaga',
                                 'guests': 5}, self.ctx)
        self.assertFalse(res['ok'])

    def test_zero_guests(self):
        res = registry.dispatch('booking', 'propose_wedding',
                                {'venue_id': str(self.hall.pk), 'day': 'ertaga',
                                 'guests': 0}, self.ctx)
        self.assertFalse(res['ok'])

    def test_prepay_hall_hits_amount_guard(self):
        """Oldindan to'lov talab qilinsa — 2 mln limitidan oshgani uchun guard
        to'xtatadi (pul HAQIQATDA ko'chadi). Prepay'siz esa 0 — bron o'tadi."""
        from booking.models import Venue
        hall = Venue.objects.create(owner=self.user, name='Prepay Zal',
                                    venue_type='wedding', is_active=True,
                                    capacity=300, price_per_day=12000000,
                                    prepay_required=True)
        res = registry.dispatch('booking', 'propose_wedding',
                                {'venue_id': str(hall.pk), 'day': 'ertaga',
                                 'guests': 100}, self.ctx)
        self.assertEqual(res['result_status'], 'limited')

    def test_requires_auth(self):
        res = registry.dispatch('booking', 'propose_wedding',
                                {'venue_id': str(self.hall.pk), 'day': 'ertaga',
                                 'guests': 100}, _fixtures.anon_ctx())
        self.assertEqual(res['result_status'], 'denied')

    def test_double_booking_blocked_at_execute(self):
        """Ikki kishi bir kunни tanlasa — ikkinchisi executor'да to'xtaydi."""
        from booking.models import VenueBooking
        other = _mk_user('998926000003')
        r1 = registry.dispatch('booking', 'propose_wedding',
                               {'venue_id': str(self.hall.pk), 'day': 'ertaga',
                                'guests': 100}, self.ctx)
        r2 = registry.dispatch('booking', 'propose_wedding',
                               {'venue_id': str(self.hall.pk), 'day': 'ertaga',
                                'guests': 120},
                               _fixtures.user_ctx(other, session_key='w2'))
        confirm.execute(r1['pending_id'], self.user)
        confirm.execute(r2['pending_id'], other)
        self.assertEqual(VenueBooking.objects.filter(venue=self.hall).count(), 1)
