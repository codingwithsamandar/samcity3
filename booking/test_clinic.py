"""Klinika (shaxsiy klinikalar) — bron turi, slot rejimi va kengaytirilgan oyna.

    python manage.py test booking.test_clinic
"""
from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from main.models import User
from booking.models import (
    Venue, VenueService, VenueStaff, VenueBooking, SLOT_TYPES,
    MAX_BOOKING_AHEAD_DAYS, CLINIC_BOOKING_AHEAD_DAYS,
    booking_ahead_days, booking_window,
)


class ClinicSetup(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(phone='+998910000301', password='x', is_active=True)
        self.patient = User.objects.create_user(phone='+998910000302', password='x', is_active=True)
        self.venue = Venue.objects.create(
            owner=self.owner, name='Shifo Klinika', venue_type='clinic',
            working_hours_start=time(9, 0), working_hours_end=time(18, 0),
            prepay_required=False)
        self.svc = VenueService.objects.create(
            venue=self.venue, name='Terapevt qabuli', price=80000, duration_minutes=30)
        self.doctor = VenueStaff.objects.create(
            venue=self.venue, name='Dr. Aziz', is_active=True)
        self.client.force_login(self.patient)


class ClinicTypeTests(ClinicSetup):
    def test_clinic_uses_slots(self):
        # Klinika slot rejimida: xizmat (qabul turi) + shifokor + vaqt tanlanadi.
        self.assertIn('clinic', SLOT_TYPES)
        self.assertTrue(self.venue.uses_slots)

    def test_clinic_type_offered_in_create_form(self):
        self.client.force_login(self.owner)
        resp = self.client.get(reverse('venue_create'))
        self.assertContains(resp, 'value="clinic"')

    def test_booking_form_shows_service_and_staff_step(self):
        # Xizmatlar server tomonda, shifokorlar esa vaqt tanlangach AJAX
        # (venue_staff_at) bilan yuklanadi — shuning uchun blok tekshiriladi.
        resp = self.client.get(reverse('venue_book', args=[self.venue.pk]))
        self.assertContains(resp, 'Terapevt qabuli')
        self.assertContains(resp, 'id="masterWrap"')
        self.assertContains(resp, 'Shifokorni tanlang')

    def test_staff_endpoint_lists_doctor(self):
        resp = self.client.get(reverse('venue_staff_at', args=[self.venue.pk]), {
            'date': (date.today() + timedelta(days=2)).isoformat(), 'time': '10:00',
        })
        names = [s['name'] for s in resp.json()['staff']]
        self.assertIn('Dr. Aziz', names)

    def test_staff_label_is_doctor_for_clinic(self):
        hall = Venue.objects.create(owner=self.owner, name='Zal', venue_type='barber')
        self.assertEqual(self.venue.staff_label, 'Shifokor')
        self.assertEqual(hall.staff_label, 'Usta')


class ClinicWindowTests(ClinicSetup):
    def _post(self, booking_date, start='10:00'):
        return self.client.post(reverse('venue_book', args=[self.venue.pk]), {
            'booking_date': booking_date.isoformat(),
            'service': str(self.svc.pk), 'staff': str(self.doctor.pk),
            'start_time': start, 'guests': '1',
        }, follow=True)

    def test_window_is_wider_for_clinic(self):
        self.assertEqual(booking_ahead_days(self.venue), CLINIC_BOOKING_AHEAD_DAYS)
        first, last = booking_window(self.venue)
        self.assertEqual((last - first).days, CLINIC_BOOKING_AHEAD_DAYS)

    def test_other_types_keep_default_window(self):
        hall = Venue.objects.create(owner=self.owner, name='To\'yxona', venue_type='wedding')
        self.assertEqual(booking_ahead_days(hall), MAX_BOOKING_AHEAD_DAYS)

    def test_date_beyond_default_window_accepted(self):
        # 7 kundan narida, lekin 30 kun ichida — klinika uchun ochiq.
        self._post(date.today() + timedelta(days=MAX_BOOKING_AHEAD_DAYS + 10))
        self.assertEqual(VenueBooking.objects.count(), 1)

    def test_date_beyond_clinic_window_rejected(self):
        resp = self._post(date.today() + timedelta(days=CLINIC_BOOKING_AHEAD_DAYS + 1))
        self.assertEqual(VenueBooking.objects.count(), 0)
        self.assertContains(resp, 'kun oldindan ochiq')

    def test_form_max_uses_clinic_window(self):
        last = booking_window(self.venue)[1]
        resp = self.client.get(reverse('venue_book', args=[self.venue.pk]))
        self.assertContains(resp, f'max="{last.isoformat()}"')

    def test_slots_endpoint_uses_clinic_window(self):
        url = reverse('venue_slots', args=[self.venue.pk])
        far = self.client.get(
            url, {'date': (date.today() + timedelta(days=MAX_BOOKING_AHEAD_DAYS + 5)).isoformat()})
        self.assertTrue(far.json()['slots'])

    def test_api_detail_exposes_window_and_label(self):
        # Mobil ilova taqvim chegarasini va «Shifokor» yorlig'ini shu
        # maydonlardan oladi — bo'lmasa ilova 365 kun ochib, server rad etardi.
        api = APIClient()
        resp = api.get(f'/api/booking/venues/{self.venue.pk}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['staff_label'], 'Shifokor')
        self.assertEqual(resp.data['max_ahead_days'], CLINIC_BOOKING_AHEAD_DAYS)
        first, last = booking_window(self.venue)
        self.assertEqual(resp.data['book_from'], first.isoformat())
        self.assertEqual(resp.data['book_until'], last.isoformat())
        self.assertTrue(resp.data['uses_slots'])

    def test_api_detail_window_default_for_other_types(self):
        hall = Venue.objects.create(owner=self.owner, name='Zal', venue_type='wedding')
        resp = APIClient().get(f'/api/booking/venues/{hall.pk}/')
        self.assertEqual(resp.data['max_ahead_days'], MAX_BOOKING_AHEAD_DAYS)
        self.assertEqual(resp.data['staff_label'], 'Usta')

    def test_api_accepts_date_inside_clinic_window(self):
        api = APIClient()
        api.force_authenticate(self.patient)
        resp = api.post(f'/api/booking/venues/{self.venue.pk}/book/', {
            'booking_date': (date.today() + timedelta(days=MAX_BOOKING_AHEAD_DAYS + 6)).isoformat(),
            'start_time': '11:00', 'service': str(self.svc.pk),
            'staff': str(self.doctor.pk),
        }, format='json')
        self.assertIn(resp.status_code, (200, 201))
        self.assertEqual(VenueBooking.objects.count(), 1)


class ClinicSlotBehaviourTests(ClinicSetup):
    def test_end_time_from_service_duration(self):
        self.client.post(reverse('venue_book', args=[self.venue.pk]), {
            'booking_date': (date.today() + timedelta(days=2)).isoformat(),
            'service': str(self.svc.pk), 'staff': str(self.doctor.pk),
            'start_time': '10:00', 'guests': '1',
        }, follow=True)
        b = VenueBooking.objects.get()
        self.assertEqual(b.start_time, time(10, 0))
        self.assertEqual(b.end_time, time(10, 30))
        self.assertEqual(b.staff, self.doctor)
        self.assertEqual(b.total_amount, self.svc.price)

    def test_same_doctor_same_time_conflicts(self):
        day = (date.today() + timedelta(days=2)).isoformat()
        data = {'booking_date': day, 'service': str(self.svc.pk),
                'staff': str(self.doctor.pk), 'start_time': '10:00', 'guests': '1'}
        self.client.post(reverse('venue_book', args=[self.venue.pk]), data, follow=True)
        resp = self.client.post(reverse('venue_book', args=[self.venue.pk]), data, follow=True)
        self.assertEqual(VenueBooking.objects.count(), 1)
        self.assertContains(resp, 'band')

    def test_other_doctor_same_time_is_free(self):
        day = (date.today() + timedelta(days=2)).isoformat()
        doctor2 = VenueStaff.objects.create(venue=self.venue, name='Dr. Nodira', is_active=True)
        base = {'booking_date': day, 'service': str(self.svc.pk),
                'start_time': '10:00', 'guests': '1'}
        self.client.post(reverse('venue_book', args=[self.venue.pk]),
                         dict(base, staff=str(self.doctor.pk)), follow=True)
        self.client.post(reverse('venue_book', args=[self.venue.pk]),
                         dict(base, staff=str(doctor2.pk)), follow=True)
        self.assertEqual(VenueBooking.objects.count(), 2)
