"""Bron tizimi testlari — slot, xizmat, jarima, no-show.

    python manage.py test booking
"""
from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from main.models import User
from booking.models import Venue, VenueService, VenueStaff, VenueBooking


def make_user(phone):
    return User.objects.create_user(phone=phone, password='x', is_active=True)


class BookingModelTests(TestCase):
    def setUp(self):
        self.owner = make_user('+998910000001')
        self.venue = Venue.objects.create(
            owner=self.owner, name='Soch Usta', venue_type='barber',
            working_hours_start=time(9, 0), working_hours_end=time(18, 0),
            cancel_penalty_percent=10, prepay_required=True)
        self.svc = VenueService.objects.create(venue=self.venue, name='Soch olish',
                                               price=30000, duration_minutes=30)
        self.master = VenueStaff.objects.create(venue=self.venue, name='Ali')
        self.tomorrow = date.today() + timedelta(days=1)

    def test_slots_generated(self):
        slots = self.venue.available_slots(self.tomorrow, staff=self.master,
                                           duration_minutes=30)
        self.assertIn('09:00', slots)
        self.assertIn('17:30', slots)

    def test_booked_slot_excluded(self):
        VenueBooking.objects.create(
            venue=self.venue, user=self.owner, status='confirmed',
            booking_date=self.tomorrow, start_time=time(9, 0), end_time=time(9, 30),
            staff=self.master, service=self.svc, total_amount=30000)
        slots = self.venue.available_slots(self.tomorrow, staff=self.master,
                                           duration_minutes=30)
        self.assertNotIn('09:00', slots)

    def test_slot_free_when_other_master_free(self):
        # 2 usta; biri 09:00 da band — slot baribir bo'sh (ikkinchisi bo'sh)
        m2 = VenueStaff.objects.create(venue=self.venue, name='Vali')
        VenueBooking.objects.create(
            venue=self.venue, user=self.owner, status='confirmed',
            booking_date=self.tomorrow, start_time=time(9, 0), end_time=time(9, 30),
            staff=self.master, service=self.svc, total_amount=30000)
        slots = self.venue.available_slots(self.tomorrow, duration_minutes=30)
        self.assertIn('09:00', slots)  # m2 bo'sh
        self.assertFalse(self.master.is_free_at(self.tomorrow, time(9, 0), 30))
        self.assertTrue(m2.is_free_at(self.tomorrow, time(9, 0), 30))

    def test_cancel_applies_penalty(self):
        b = VenueBooking.objects.create(
            venue=self.venue, user=self.owner, status='confirmed',
            booking_date=self.tomorrow, start_time=time(10, 0),
            total_amount=30000, paid_amount=30000)
        b.mark_cancelled()
        self.assertEqual(b.status, 'cancelled')
        self.assertEqual(b.penalty_amount, 3000)   # 10%
        self.assertEqual(b.refund_amount, 27000)

    def test_penalty_capped_at_15(self):
        self.venue.cancel_penalty_percent = 99  # noto'g'ri qiymat
        self.assertEqual(self.venue.penalty_percent, 15)

    def test_no_show_command(self):
        from django.core.management import call_command
        past = timezone.localtime() - timedelta(hours=2)
        VenueBooking.objects.create(
            venue=self.venue, user=self.owner, status='confirmed',
            booking_date=past.date(), start_time=past.time(),
            total_amount=30000, paid_amount=30000)
        call_command('mark_no_shows')
        b = VenueBooking.objects.first()
        self.assertEqual(b.status, 'no_show')
        self.assertEqual(b.penalty_amount, 3000)


class BookingAPITests(TestCase):
    def setUp(self):
        self.owner = make_user('+998910000010')
        self.user = make_user('+998910000011')
        self.venue = Venue.objects.create(
            owner=self.owner, name='Salon', venue_type='barber',
            working_hours_start=time(9, 0), working_hours_end=time(18, 0),
            cancel_penalty_percent=10)
        self.svc = VenueService.objects.create(venue=self.venue, name='Soch',
                                               price=40000, duration_minutes=30)
        self.master = VenueStaff.objects.create(venue=self.venue, name='Vali')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.day = (date.today() + timedelta(days=2)).isoformat()

    def test_slots_endpoint(self):
        r = self.client.get(reverse('api:venue-slots', args=[self.venue.id]),
                            {'date': self.day, 'service': str(self.svc.id)})
        self.assertEqual(r.status_code, 200)
        self.assertIn('09:00', r.data['slots'])

    def test_book_with_service_sets_total(self):
        r = self.client.post(reverse('api:venue-book', args=[self.venue.id]),
                             {'booking_date': self.day, 'start_time': '10:00',
                              'service': str(self.svc.id), 'staff': str(self.master.id)},
                             format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['total_amount'], 40000)
        self.assertEqual(r.data['status'], 'pending')

    def test_same_staff_slot_conflict(self):
        self.client.post(reverse('api:venue-book', args=[self.venue.id]),
                         {'booking_date': self.day, 'start_time': '10:00',
                          'service': str(self.svc.id), 'staff': str(self.master.id)},
                         format='json')
        r = self.client.post(reverse('api:venue-book', args=[self.venue.id]),
                             {'booking_date': self.day, 'start_time': '10:00',
                              'service': str(self.svc.id), 'staff': str(self.master.id)},
                             format='json')
        self.assertEqual(r.status_code, 409)

    def test_book_requires_service_for_slot_venue(self):
        r = self.client.post(reverse('api:venue-book', args=[self.venue.id]),
                             {'booking_date': self.day, 'start_time': '10:00'},
                             format='json')
        self.assertEqual(r.status_code, 400)


class SlotPerformanceTests(TestCase):
    """N+1 himoyasi: slot/usta-bo'shlik hisobi BIR nechta so'rovda bo'lishi kerak
    (usta yoki bron soniga proporsional EMAS)."""

    def setUp(self):
        self.owner = make_user('+998910000099')
        self.venue = Venue.objects.create(
            owner=self.owner, name='Katta Salon', venue_type='barber',
            working_hours_start=time(9, 0), working_hours_end=time(18, 0))
        self.svc = VenueService.objects.create(
            venue=self.venue, name='Soch', price=30000, duration_minutes=30)
        # Ko'p usta + ko'p bron — eski kodda yuzlab so'rov bo'lardi
        self.masters = [VenueStaff.objects.create(venue=self.venue, name=f'Usta {i}')
                        for i in range(5)]
        self.day = date.today() + timedelta(days=3)
        for i, m in enumerate(self.masters):
            for h in (9, 11, 14):
                VenueBooking.objects.create(
                    venue=self.venue, user=self.owner, status='confirmed',
                    booking_date=self.day, start_time=time(h, 0), end_time=time(h, 30),
                    staff=m, service=self.svc, total_amount=30000)

    def _count(self, fn):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            fn()
        return len(ctx.captured_queries)

    def _small_venue(self):
        """1 usta, 0 bron — taqqoslash uchun."""
        v = Venue.objects.create(
            owner=self.owner, name='Kichik', venue_type='barber',
            working_hours_start=time(9, 0), working_hours_end=time(18, 0))
        VenueStaff.objects.create(venue=v, name='Yagona')
        return v

    def test_available_slots_no_n_plus_one(self):
        # So'rovlar soni usta/bron soniga qarab O'SMASLIGI kerak.
        small = self._small_venue()
        n_small = self._count(lambda: small.available_slots(self.day, duration_minutes=30))
        n_big = self._count(lambda: self.venue.available_slots(self.day, duration_minutes=30))
        self.assertEqual(n_big, n_small)   # 5 usta + 15 bron = 1 usta bilan bir xil
        self.assertLessEqual(n_big, 6)     # konstanta (N+1 bo'lsa 15+ bo'lardi)

    def test_free_staff_at_no_n_plus_one(self):
        small = self._small_venue()
        n_small = self._count(lambda: small.free_staff_at(self.day, time(9, 0), 30))
        n_big = self._count(lambda: self.venue.free_staff_at(self.day, time(9, 0), 30))
        self.assertEqual(n_big, n_small)
        self.assertLessEqual(n_big, 4)
