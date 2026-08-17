"""Usta panelida: band vaqtlar, mijoz, xizmat va TO'LOV holati.

    python manage.py test booking.test_staff_payment_view
"""
from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse

from main.models import User
from booking.models import Venue, VenueService, VenueStaff, VenueBooking


class PaymentStateTests(TestCase):
    """Model darajasidagi to'lov holati — panel shuni ko'rsatadi."""

    def setUp(self):
        self.owner = User.objects.create_user(phone='+998910000801', password='x', is_active=True)
        self.mijoz = User.objects.create_user(phone='+998910000802', password='x', is_active=True)

    def _bron(self, prepay, paid=0, total=30000):
        v = Venue.objects.create(owner=self.owner, name='J', venue_type='barber',
                                 prepay_required=prepay)
        return VenueBooking.objects.create(
            venue=v, user=self.mijoz, status='confirmed', booking_date=date.today(),
            total_amount=total, paid_amount=paid)

    def test_paid_state(self):
        b = self._bron(prepay=True, paid=30000)
        self.assertEqual(b.payment_state[0], 'paid')
        self.assertEqual(b.amount_due, 0)

    def test_awaiting_when_prepay_required(self):
        b = self._bron(prepay=True, paid=0)
        self.assertEqual(b.payment_state[0], 'awaiting')
        self.assertEqual(b.amount_due, 30000)

    def test_onsite_when_prepay_not_required(self):
        b = self._bron(prepay=False, paid=0)
        self.assertEqual(b.payment_state[0], 'onsite')

    def test_partial_payment_leaves_due(self):
        b = self._bron(prepay=True, paid=10000)
        self.assertEqual(b.payment_state[0], 'paid')   # qisman ham to'langan
        self.assertEqual(b.amount_due, 20000)

    def test_amount_due_never_negative(self):
        b = self._bron(prepay=True, paid=50000, total=30000)
        self.assertEqual(b.amount_due, 0)


class StaffPanelPaymentTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(phone='+998910000811', password='x', is_active=True)
        self.ali = User.objects.create_user(phone='+998910000812', password='x', is_active=True)
        self.mijoz = User.objects.create_user(phone='+998910000813', password='x', is_active=True)
        self.mijoz.name = 'Aziz Karimov'
        self.mijoz.save(update_fields=['name'])

        self.venue = Venue.objects.create(
            owner=self.owner, name='Soch Usta', venue_type='barber',
            working_hours_start=time(9), working_hours_end=time(18),
            prepay_required=True)
        self.svc = VenueService.objects.create(venue=self.venue, name='Soch olish',
                                               price=30000, duration_minutes=30)
        self.ali_staff = VenueStaff.objects.create(venue=self.venue, name='Ali', user=self.ali)
        self.ertaga = date.today() + timedelta(days=1)
        self.client.force_login(self.ali)

    def _bron(self, kun=None, vaqt=time(10), paid=0):
        return VenueBooking.objects.create(
            venue=self.venue, user=self.mijoz, staff=self.ali_staff, service=self.svc,
            status='confirmed', booking_date=kun or self.ertaga,
            start_time=vaqt, end_time=time(vaqt.hour, 30),
            total_amount=30000, paid_amount=paid)

    def _panel(self, kun=None):
        return self.client.get(reverse('staff_panel'),
                               {'kun': (kun or self.ertaga).isoformat()})

    # ── Kim, qachon, qanday xizmat ──────────────────────────────────────────
    def test_shows_who_booked_what_and_when(self):
        self._bron(vaqt=time(14))
        resp = self._panel()
        self.assertContains(resp, 'Aziz Karimov')       # kim
        self.assertContains(resp, '14:00')              # qachon
        self.assertContains(resp, 'Soch olish')         # qanday xizmat
        self.assertContains(resp, '+998910000813')      # telefoni

    def test_selected_day_busy_slots_listed(self):
        """Tanlangan kun bronlari ko'rinadi (ilgari faqat bugungisi edi)."""
        self._bron(kun=self.ertaga, vaqt=time(11))
        ctx = self._panel().context
        self.assertEqual(len(ctx['bosh_vaqtlar'][0]['band']), 1)

    def test_other_day_not_mixed_in(self):
        self._bron(kun=self.ertaga + timedelta(days=1), vaqt=time(11))
        ctx = self._panel(self.ertaga).context
        self.assertEqual(len(ctx['bosh_vaqtlar'][0]['band']), 0)

    # ── To'lov holati ───────────────────────────────────────────────────────
    def test_unpaid_shows_awaiting(self):
        self._bron(paid=0)
        resp = self._panel()
        self.assertContains(resp, "To&#x27;lov kutilmoqda")
        self.assertContains(resp, 'pay-awaiting')

    def test_paid_shows_paid(self):
        self._bron(paid=30000)
        resp = self._panel()
        self.assertContains(resp, "To&#x27;langan")
        self.assertContains(resp, 'pay-paid')

    def test_onsite_when_venue_has_no_prepay(self):
        self.venue.prepay_required = False
        self.venue.save(update_fields=['prepay_required'])
        self._bron(paid=0)
        resp = self._panel()
        self.assertContains(resp, "Joyida to&#x27;laydi")
        self.assertContains(resp, 'pay-onsite')

    def test_amount_shown(self):
        self._bron()
        self.assertContains(self._panel(), '30000')

    # ── Kun yig'indisi ──────────────────────────────────────────────────────
    def test_day_totals(self):
        self._bron(vaqt=time(10), paid=30000)
        self._bron(vaqt=time(11), paid=0)
        bv = self._panel().context['bosh_vaqtlar'][0]
        self.assertEqual(bv['yigilgan'], 30000)
        self.assertEqual(bv['kutilayotgan'], 30000)

    def test_completed_not_counted_as_awaiting(self):
        b = self._bron(paid=0)
        b.status = 'completed'
        b.save(update_fields=['status'])
        self.assertEqual(self._panel().context['bosh_vaqtlar'][0]['kutilayotgan'], 0)

    # ── Chegaralar ──────────────────────────────────────────────────────────
    def test_cancelled_booking_not_listed(self):
        b = self._bron()
        b.status = 'cancelled'
        b.save(update_fields=['status'])
        self.assertEqual(len(self._panel().context['bosh_vaqtlar'][0]['band']), 0)

    def test_other_staff_booking_not_listed(self):
        vali = VenueStaff.objects.create(venue=self.venue, name='Vali')
        VenueBooking.objects.create(
            venue=self.venue, user=self.mijoz, staff=vali, service=self.svc,
            status='confirmed', booking_date=self.ertaga, start_time=time(12),
            total_amount=30000)
        self.assertEqual(len(self._panel().context['bosh_vaqtlar'][0]['band']), 0)
