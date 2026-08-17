"""Usta paneli testlari — jadval, ruxsat chegarasi, hisobga bog'lash.

    python manage.py test booking.test_staff_panel
"""
from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse

from main.models import User
from booking.models import Venue, VenueService, VenueStaff, VenueBooking


class StaffPanelTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(phone='+998910000601', password='x', is_active=True)
        self.ali = User.objects.create_user(phone='+998910000602', password='x', is_active=True)
        self.vali = User.objects.create_user(phone='+998910000603', password='x', is_active=True)
        self.mijoz = User.objects.create_user(phone='+998910000604', password='x', is_active=True)

        self.venue = Venue.objects.create(owner=self.owner, name='Soch Usta',
                                          venue_type='barber',
                                          working_hours_start=time(9), working_hours_end=time(18))
        self.svc = VenueService.objects.create(venue=self.venue, name='Soch olish', price=30000)
        self.ali_staff = VenueStaff.objects.create(venue=self.venue, name='Ali', user=self.ali)
        self.vali_staff = VenueStaff.objects.create(venue=self.venue, name='Vali', user=self.vali)

    def _bron(self, staff, kun=None, vaqt=time(10), status='confirmed'):
        return VenueBooking.objects.create(
            venue=self.venue, user=self.mijoz, staff=staff, service=self.svc,
            status=status, booking_date=kun or date.today(), start_time=vaqt)

    # ── Kirish ──────────────────────────────────────────────────────────────
    def test_login_required(self):
        self.assertEqual(self.client.get(reverse('staff_panel')).status_code, 302)

    def test_non_staff_sees_empty_state(self):
        self.client.force_login(self.mijoz)
        resp = self.client.get(reverse('staff_panel'))
        self.assertContains(resp, 'usta sifatida')
        self.assertEqual(list(resp.context['roles']), [])

    # ── Jadval ──────────────────────────────────────────────────────────────
    def test_today_and_upcoming_split(self):
        self._bron(self.ali_staff, date.today())
        self._bron(self.ali_staff, date.today() + timedelta(days=2))
        self.client.force_login(self.ali)
        ctx = self.client.get(reverse('staff_panel')).context
        self.assertEqual(len(ctx['bugun']), 1)
        self.assertEqual(len(ctx['keyingi']), 1)

    def test_past_bookings_excluded(self):
        self._bron(self.ali_staff, date.today() - timedelta(days=3))
        self.client.force_login(self.ali)
        ctx = self.client.get(reverse('staff_panel')).context
        self.assertEqual(len(ctx['bugun']) + len(ctx['keyingi']), 0)

    def test_cancelled_booking_excluded(self):
        self._bron(self.ali_staff, status='cancelled')
        self.client.force_login(self.ali)
        self.assertEqual(len(self.client.get(reverse('staff_panel')).context['bugun']), 0)

    def test_completed_count_shown(self):
        self._bron(self.ali_staff, status='completed')
        self.client.force_login(self.ali)
        self.assertEqual(self.client.get(reverse('staff_panel')).context['bajarilgan'], 1)

    # ── Ruxsat chegarasi: usta FAQAT o'ziniki ko'radi ───────────────────────
    def test_staff_sees_only_own_bookings(self):
        self._bron(self.ali_staff)
        vali_bron = self._bron(self.vali_staff, vaqt=time(11))
        self.client.force_login(self.ali)
        resp = self.client.get(reverse('staff_panel'))
        ids = [b.pk for b in resp.context['bugun']]
        self.assertNotIn(vali_bron.pk, ids)
        self.assertEqual(len(ids), 1)

    def test_staff_of_other_venue_not_shown(self):
        boshqa = Venue.objects.create(owner=self.owner, name='Boshqa', venue_type='barber')
        begona = VenueStaff.objects.create(venue=boshqa, name='Begona')
        b = VenueBooking.objects.create(venue=boshqa, user=self.mijoz, staff=begona,
                                        status='confirmed', booking_date=date.today())
        self.client.force_login(self.ali)
        self.assertNotIn(b.pk, [x.pk for x in
                                self.client.get(reverse('staff_panel')).context['bugun']])

    # ── Yakunlash ───────────────────────────────────────────────────────────
    def test_staff_completes_own_booking(self):
        b = self._bron(self.ali_staff)
        self.client.force_login(self.ali)
        self.client.post(reverse('staff_booking_complete', args=[b.pk]), follow=True)
        b.refresh_from_db()
        self.ali_staff.refresh_from_db()
        self.assertEqual(b.status, 'completed')
        self.assertEqual(self.ali_staff.completed_count, 1)

    def test_staff_cannot_complete_others_booking(self):
        b = self._bron(self.vali_staff)
        self.client.force_login(self.ali)
        resp = self.client.post(reverse('staff_booking_complete', args=[b.pk]), follow=True)
        b.refresh_from_db()
        self.assertEqual(b.status, 'confirmed')
        self.assertContains(resp, 'biriktirilmagan')

    def test_cannot_complete_cancelled_booking(self):
        b = self._bron(self.ali_staff, status='cancelled')
        self.client.force_login(self.ali)
        self.client.post(reverse('staff_booking_complete', args=[b.pk]), follow=True)
        b.refresh_from_db()
        self.assertEqual(b.status, 'cancelled')

    def test_complete_requires_post(self):
        b = self._bron(self.ali_staff)
        self.client.force_login(self.ali)
        self.assertEqual(
            self.client.get(reverse('staff_booking_complete', args=[b.pk])).status_code, 405)

    # ── Hisobga bog'lash (telefon orqali) ───────────────────────────────────
    def test_owner_adding_staff_links_existing_user(self):
        self.client.force_login(self.owner)
        self.client.post(reverse('staff_add', args=[self.venue.pk]),
                         {'name': 'Yangi usta', 'phone': '+998910000604'}, follow=True)
        st = VenueStaff.objects.get(name='Yangi usta')
        self.assertEqual(st.user_id, self.mijoz.pk)

    def test_unknown_phone_leaves_staff_unlinked(self):
        self.client.force_login(self.owner)
        resp = self.client.post(reverse('staff_add', args=[self.venue.pk]),
                                {'name': 'Notanish', 'phone': '+998900000000'}, follow=True)
        self.assertIsNone(VenueStaff.objects.get(name='Notanish').user_id)
        self.assertContains(resp, 'topilmadi')

    def test_link_matches_last_nine_digits(self):
        """Raqam turli formatda yozilishi mumkin — oxirgi 9 raqam bo'yicha."""
        st = VenueStaff.objects.create(venue=self.venue, name='Format', phone='910000604')
        self.assertEqual(st.link_user_by_phone(), self.mijoz)

    # ── Navigatsiya ─────────────────────────────────────────────────────────
    def test_nav_hidden_for_non_staff(self):
        self.client.force_login(self.mijoz)
        self.assertNotIn(reverse('staff_panel'),
                         self.client.get(reverse('home')).content.decode())

    def test_nav_shown_for_staff(self):
        self._bron(self.ali_staff)
        self.client.force_login(self.ali)
        html = self.client.get(reverse('home')).content.decode()
        self.assertGreaterEqual(html.count(reverse('staff_panel')), 4)
        self.assertIn('nav-usta', html)
