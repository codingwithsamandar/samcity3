"""Xizmat davomiyligi taxmini — haqiqiy tarixdan o'rganish.

    python manage.py test booking.test_estimates
"""
from datetime import date, datetime, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from main.models import User
from booking.models import Venue, VenueService, VenueStaff, VenueBooking
from booking.estimates import estimate_minutes, estimate_label, MIN_SAMPLES


class EstimateTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(phone='+998910000901', password='x', is_active=True)
        self.ali = User.objects.create_user(phone='+998910000902', password='x', is_active=True)
        self.mijoz = User.objects.create_user(phone='+998910000903', password='x', is_active=True)
        self.venue = Venue.objects.create(
            owner=self.owner, name='Soch Usta', venue_type='barber',
            working_hours_start=time(9), working_hours_end=time(18))
        self.svc = VenueService.objects.create(
            venue=self.venue, name='Soch olish', price=30000, duration_minutes=30)
        self.ali_staff = VenueStaff.objects.create(venue=self.venue, name='Ali', user=self.ali)
        self.vali_staff = VenueStaff.objects.create(venue=self.venue, name='Vali')

    def _tarix(self, staff, minutlar):
        """Yakunlangan bronlar tarixini yaratadi."""
        for i, m in enumerate(minutlar):
            VenueBooking.objects.create(
                venue=self.venue, user=self.mijoz, staff=staff, service=self.svc,
                status='completed', booking_date=date.today() - timedelta(days=i + 1),
                start_time=time(10), actual_minutes=m,
                completed_at=timezone.now() - timedelta(days=i + 1))

    # ── Tarix yo'q — rejadagi qiymat ────────────────────────────────────────
    def test_falls_back_to_plan_without_history(self):
        mins, source = estimate_minutes(self.svc, self.ali_staff)
        self.assertEqual(mins, 30)
        self.assertEqual(source, 'plan')

    def test_no_label_when_only_plan(self):
        """Rejani 'taxminan' deb ko'rsatish chalg'itadi — matn bo'lmasin."""
        self.assertIsNone(estimate_label(self.svc, self.ali_staff))

    def test_below_min_samples_still_plan(self):
        self._tarix(self.ali_staff, [20] * (MIN_SAMPLES - 1))
        self.assertEqual(estimate_minutes(self.svc, self.ali_staff)[1], 'plan')

    # ── Usta tarixi ─────────────────────────────────────────────────────────
    def test_uses_staff_history_when_enough(self):
        self._tarix(self.ali_staff, [20, 22, 21, 19, 20])
        mins, source = estimate_minutes(self.svc, self.ali_staff)
        self.assertEqual(source, 'staff')
        self.assertEqual(mins, 20)          # mediana

    def test_median_ignores_forgotten_entry(self):
        """Bitta unutilgan yozuv (2 soat) taxminni buzmasin."""
        self._tarix(self.ali_staff, [20, 21, 20, 22, 120])
        mins, _ = estimate_minutes(self.svc, self.ali_staff)
        self.assertLess(mins, 30)

    def test_label_names_the_staff(self):
        self._tarix(self.ali_staff, [25, 25, 26, 24, 25])
        self.assertIn('Ali', estimate_label(self.svc, self.ali_staff))
        self.assertIn('25', estimate_label(self.svc, self.ali_staff))

    def test_staff_estimates_are_separate(self):
        """Har usta o'z tezligiga ega — biriniki ikkinchisiga o'tmasin."""
        self._tarix(self.ali_staff, [20, 20, 21, 19, 20])
        self._tarix(self.vali_staff, [40, 41, 39, 40, 40])
        self.assertEqual(estimate_minutes(self.svc, self.ali_staff)[0], 20)
        self.assertEqual(estimate_minutes(self.svc, self.vali_staff)[0], 40)

    def test_service_history_used_for_new_staff(self):
        """Yangi ustada tarix yo'q — xizmatning umumiy tarixiga tayanadi."""
        self._tarix(self.vali_staff, [25, 26, 24, 25, 25])
        yangi = VenueStaff.objects.create(venue=self.venue, name='Yangi')
        mins, source = estimate_minutes(self.svc, yangi)
        self.assertEqual(source, 'service')
        self.assertEqual(mins, 25)

    # ── O'lchov yig'ilishi ──────────────────────────────────────────────────
    def test_completing_records_actual_minutes(self):
        b = VenueBooking.objects.create(
            venue=self.venue, user=self.mijoz, staff=self.ali_staff, service=self.svc,
            status='confirmed', booking_date=date.today(),
            start_time=(timezone.localtime() - timedelta(minutes=25)).time())
        self.client.force_login(self.ali)
        self.client.post(reverse('staff_booking_complete', args=[b.pk]), follow=True)
        b.refresh_from_db()
        self.assertEqual(b.status, 'completed')
        self.assertIsNotNone(b.completed_at)
        self.assertIsNotNone(b.actual_minutes)
        self.assertAlmostEqual(b.actual_minutes, 25, delta=2)

    def test_absurd_duration_not_recorded(self):
        """Ertasiga bosilgan «Yakunlandi» o'lchov sifatida yozilmaydi."""
        b = VenueBooking.objects.create(
            venue=self.venue, user=self.mijoz, staff=self.ali_staff, service=self.svc,
            status='confirmed', booking_date=date.today() - timedelta(days=2),
            start_time=time(10))
        b.mark_completed()
        b.refresh_from_db()
        self.assertEqual(b.status, 'completed')
        self.assertIsNone(b.actual_minutes)      # 8 soatdan oshgan — yaroqsiz

    def test_panel_shows_estimate(self):
        self._tarix(self.ali_staff, [20, 21, 20, 19, 20])
        ertaga = date.today() + timedelta(days=1)
        VenueBooking.objects.create(
            venue=self.venue, user=self.mijoz, staff=self.ali_staff, service=self.svc,
            status='confirmed', booking_date=ertaga, start_time=time(11))
        self.client.force_login(self.ali)
        resp = self.client.get(reverse('staff_panel'), {'kun': ertaga.isoformat()})
        self.assertContains(resp, 'odatda')
