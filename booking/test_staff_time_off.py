"""Usta o'z bo'sh vaqtini boshqaradi — yopish va qayta ochish.

    python manage.py test booking.test_staff_time_off
"""
from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse

from main.models import User
from booking.models import (
    Venue, VenueService, VenueStaff, VenueBooking, StaffTimeOff,
)


class StaffTimeOffTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(phone='+998910000701', password='x', is_active=True)
        self.ali = User.objects.create_user(phone='+998910000702', password='x', is_active=True)
        self.vali = User.objects.create_user(phone='+998910000703', password='x', is_active=True)
        self.mijoz = User.objects.create_user(phone='+998910000704', password='x', is_active=True)
        self.venue = Venue.objects.create(
            owner=self.owner, name='Soch Usta', venue_type='barber',
            working_hours_start=time(9), working_hours_end=time(18))
        VenueService.objects.create(venue=self.venue, name='Soch olish',
                                    price=30000, duration_minutes=30)
        self.ali_staff = VenueStaff.objects.create(venue=self.venue, name='Ali', user=self.ali)
        self.vali_staff = VenueStaff.objects.create(venue=self.venue, name='Vali', user=self.vali)
        self.ertaga = date.today() + timedelta(days=1)

    def _yop(self, **data):
        data.setdefault('kun', self.ertaga.isoformat())
        return self.client.post(
            reverse('staff_time_off_add', args=[self.ali_staff.pk]), data, follow=True)

    # ── Yopish slotlardan olib tashlaydi ────────────────────────────────────
    def test_closing_hour_removes_slots(self):
        self.client.force_login(self.ali)
        self.assertIn('12:00', self.venue.available_slots(self.ertaga, staff=self.ali_staff))
        self._yop(start_time='12:00', end_time='13:00', reason='Tushlik')
        keyin = self.venue.available_slots(self.ertaga, staff=self.ali_staff)
        self.assertNotIn('12:00', keyin)
        self.assertNotIn('12:30', keyin)
        self.assertIn('13:00', keyin)      # tugagandan keyin yana ochiq
        self.assertIn('09:00', keyin)      # boshqa vaqtlar tegilmagan

    def test_whole_day_closes_everything(self):
        self.client.force_login(self.ali)
        self._yop(whole_day='on', reason='Dam olish')
        self.assertEqual(self.venue.available_slots(self.ertaga, staff=self.ali_staff), [])

    def test_closing_affects_only_own_schedule(self):
        self.client.force_login(self.ali)
        self._yop(whole_day='on')
        self.assertTrue(self.venue.available_slots(self.ertaga, staff=self.vali_staff))
        self.assertTrue(self.venue.available_slots(self.ertaga))

    def test_client_cannot_book_closed_time(self):
        """Yopilgan vaqt mijozning bron formasida ham ko'rinmaydi."""
        self.client.force_login(self.ali)
        self._yop(start_time='12:00', end_time='13:00')
        self.client.force_login(self.mijoz)
        slots = self.client.get(
            reverse('venue_slots', args=[self.venue.pk]),
            {'date': self.ertaga.isoformat(), 'staff': str(self.ali_staff.pk)},
        ).json()['slots']
        self.assertNotIn('12:00', slots)

    def test_free_staff_at_skips_closed(self):
        self.client.force_login(self.ali)
        self._yop(start_time='12:00', end_time='13:00')
        free = self.venue.free_staff_at(self.ertaga, time(12, 0))
        self.assertNotIn(self.ali_staff, free)
        self.assertIn(self.vali_staff, free)

    # ── Qayta ochish ────────────────────────────────────────────────────────
    def test_reopening_restores_slots(self):
        self.client.force_login(self.ali)
        self._yop(start_time='12:00', end_time='13:00')
        off = StaffTimeOff.objects.get()
        self.client.post(reverse('staff_time_off_delete', args=[off.pk]), follow=True)
        self.assertIn('12:00', self.venue.available_slots(self.ertaga, staff=self.ali_staff))

    # ── Ruxsat chegarasi ────────────────────────────────────────────────────
    def test_cannot_close_someone_elses_schedule(self):
        self.client.force_login(self.vali)
        resp = self.client.post(
            reverse('staff_time_off_add', args=[self.ali_staff.pk]),
            {'kun': self.ertaga.isoformat(), 'whole_day': 'on'}, follow=True)
        self.assertEqual(StaffTimeOff.objects.count(), 0)
        self.assertContains(resp, 'sizga tegishli emas')

    def test_cannot_reopen_someone_elses(self):
        off = StaffTimeOff.objects.create(staff=self.ali_staff, date=self.ertaga)
        self.client.force_login(self.vali)
        self.client.post(reverse('staff_time_off_delete', args=[off.pk]), follow=True)
        self.assertTrue(StaffTimeOff.objects.filter(pk=off.pk).exists())

    # ── Mavjud bron himoyasi ────────────────────────────────────────────────
    def test_cannot_close_over_existing_booking(self):
        VenueBooking.objects.create(
            venue=self.venue, user=self.mijoz, staff=self.ali_staff, status='confirmed',
            booking_date=self.ertaga, start_time=time(12), end_time=time(12, 30))
        self.client.force_login(self.ali)
        resp = self._yop(start_time='12:00', end_time='13:00')
        self.assertEqual(StaffTimeOff.objects.count(), 0)
        self.assertContains(resp, 'bron bor')

    def test_can_close_hour_without_booking(self):
        VenueBooking.objects.create(
            venue=self.venue, user=self.mijoz, staff=self.ali_staff, status='confirmed',
            booking_date=self.ertaga, start_time=time(15), end_time=time(15, 30))
        self.client.force_login(self.ali)
        self._yop(start_time='12:00', end_time='13:00')
        self.assertEqual(StaffTimeOff.objects.count(), 1)

    def test_whole_day_blocked_by_any_booking(self):
        VenueBooking.objects.create(
            venue=self.venue, user=self.mijoz, staff=self.ali_staff, status='confirmed',
            booking_date=self.ertaga, start_time=time(15), end_time=time(15, 30))
        self.client.force_login(self.ali)
        resp = self._yop(whole_day='on')
        self.assertEqual(StaffTimeOff.objects.count(), 0)
        self.assertContains(resp, 'bron bor')

    # ── Kiritish tekshiruvlari ──────────────────────────────────────────────
    def test_end_must_be_after_start(self):
        self.client.force_login(self.ali)
        resp = self._yop(start_time='13:00', end_time='12:00')
        self.assertEqual(StaffTimeOff.objects.count(), 0)
        self.assertContains(resp, 'keyin bo')

    def test_time_required_unless_whole_day(self):
        self.client.force_login(self.ali)
        resp = self._yop(reason='Sababsiz')
        self.assertEqual(StaffTimeOff.objects.count(), 0)
        self.assertContains(resp, 'vaqtni tanlang')

    def test_date_outside_booking_window_rejected(self):
        self.client.force_login(self.ali)
        resp = self._yop(kun=(date.today() + timedelta(days=60)).isoformat(),
                         whole_day='on')
        self.assertEqual(StaffTimeOff.objects.count(), 0)
        self.assertContains(resp, 'kun oldindan ochiq')

    # ── Panelda ko'rinishi ──────────────────────────────────────────────────
    def test_panel_shows_closed_times(self):
        StaffTimeOff.objects.create(staff=self.ali_staff, date=self.ertaga,
                                    start_time=time(12), end_time=time(13),
                                    reason='Tushlik')
        self.client.force_login(self.ali)
        resp = self.client.get(reverse('staff_panel'), {'kun': self.ertaga.isoformat()})
        self.assertContains(resp, 'Tushlik')
        self.assertContains(resp, 'Yopilgan vaqtlar')

    def test_panel_shows_free_slots(self):
        self.client.force_login(self.ali)
        resp = self.client.get(reverse('staff_panel'), {'kun': self.ertaga.isoformat()})
        self.assertContains(resp, "Bo'sh vaqtlarim")
        self.assertTrue(resp.context['bosh_vaqtlar'][0]['slotlar'])

    def test_whole_day_flag_in_panel(self):
        StaffTimeOff.objects.create(staff=self.ali_staff, date=self.ertaga)
        self.client.force_login(self.ali)
        resp = self.client.get(reverse('staff_panel'), {'kun': self.ertaga.isoformat()})
        self.assertTrue(resp.context['bosh_vaqtlar'][0]['kun_yopiq'])
        self.assertContains(resp, 'butunlay yopilgan')
