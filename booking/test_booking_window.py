"""Bron oynasi (bir hafta) testlari — veb forma, AJAX slotlar va API.

    python manage.py test booking.test_booking_window
"""
from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from main.models import User
from booking.models import (
    Venue, VenueService, VenueBooking, MAX_BOOKING_AHEAD_DAYS, booking_window,
)


class BookingWindowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(phone='+998910000201', password='x', is_active=True)
        self.client_user = User.objects.create_user(
            phone='+998910000202', password='x', is_active=True)
        self.venue = Venue.objects.create(
            owner=self.owner, name='Soch Usta', venue_type='barber',
            working_hours_start=time(9, 0), working_hours_end=time(18, 0),
            prepay_required=False)
        self.svc = VenueService.objects.create(
            venue=self.venue, name='Soch olish', price=30000, duration_minutes=30)
        self.client.force_login(self.client_user)

    def _post(self, booking_date, start='10:00'):
        return self.client.post(reverse('venue_book', args=[self.venue.pk]), {
            'booking_date': booking_date.isoformat(),
            'service': str(self.svc.pk), 'start_time': start, 'guests': '1',
        }, follow=True)

    # ── Oyna chegaralari ────────────────────────────────────────────────────
    def test_window_is_one_week(self):
        first, last = booking_window()
        self.assertEqual(first, date.today())
        self.assertEqual((last - first).days, MAX_BOOKING_AHEAD_DAYS)

    def test_date_inside_window_accepted(self):
        self._post(date.today() + timedelta(days=3))
        self.assertEqual(VenueBooking.objects.count(), 1)

    def test_last_allowed_day_accepted(self):
        self._post(booking_window()[1])
        self.assertEqual(VenueBooking.objects.count(), 1)

    def test_beyond_window_rejected(self):
        resp = self._post(date.today() + timedelta(days=MAX_BOOKING_AHEAD_DAYS + 1))
        self.assertEqual(VenueBooking.objects.count(), 0)
        self.assertContains(resp, 'kun oldindan ochiq')

    def test_past_date_rejected(self):
        resp = self._post(date.today() - timedelta(days=1))
        self.assertEqual(VenueBooking.objects.count(), 0)
        self.assertContains(resp, "O&#x27;tgan sanaga")

    def test_missing_date_rejected(self):
        resp = self.client.post(reverse('venue_book', args=[self.venue.pk]), {
            'service': str(self.svc.pk), 'start_time': '10:00',
        }, follow=True)
        self.assertEqual(VenueBooking.objects.count(), 0)
        self.assertContains(resp, 'sanani tanlang')

    # ── Forma maydonida min/max bo'lishi ────────────────────────────────────
    def test_form_carries_min_and_max(self):
        first, last = booking_window()
        resp = self.client.get(reverse('venue_book', args=[self.venue.pk]))
        self.assertContains(resp, f'min="{first.isoformat()}"')
        self.assertContains(resp, f'max="{last.isoformat()}"')

    # ── Slot AJAX ham oynadan tashqariga slot bermaydi ──────────────────────
    def test_slots_endpoint_respects_window(self):
        url = reverse('venue_slots', args=[self.venue.pk])
        ok = self.client.get(url, {'date': (date.today() + timedelta(days=2)).isoformat()})
        self.assertTrue(ok.json()['slots'])

        far = self.client.get(
            url, {'date': (date.today() + timedelta(days=MAX_BOOKING_AHEAD_DAYS + 5)).isoformat()})
        self.assertEqual(far.json()['slots'], [])
        self.assertEqual(far.json()['error'], 'out_of_window')

    # ── API ham xuddi shu qoidada ───────────────────────────────────────────
    def test_api_rejects_date_beyond_window(self):
        api = APIClient()
        api.force_authenticate(self.client_user)
        resp = api.post(f'/api/booking/venues/{self.venue.pk}/book/', {
            'booking_date': (date.today() + timedelta(days=MAX_BOOKING_AHEAD_DAYS + 3)).isoformat(),
            'start_time': '10:00', 'service': str(self.svc.pk),
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('booking_date', resp.data)
        self.assertEqual(VenueBooking.objects.count(), 0)

    def test_api_accepts_date_inside_window(self):
        api = APIClient()
        api.force_authenticate(self.client_user)
        resp = api.post(f'/api/booking/venues/{self.venue.pk}/book/', {
            'booking_date': (date.today() + timedelta(days=2)).isoformat(),
            'start_time': '11:00', 'service': str(self.svc.pk),
        }, format='json')
        self.assertIn(resp.status_code, (200, 201))
        self.assertEqual(VenueBooking.objects.count(), 1)
