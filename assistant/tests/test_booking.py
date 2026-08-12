"""FAZA B — sartaroshxona broni: find_venue → service → slot → confirm → VenueBooking.

⚠️ Bron FAQAT tasdiqdan keyin yaratiladi (arxitektura himoyasi — delivery bilan
bir xil). propose_booking → PendingAction, place_booking (@executor) → VenueBooking.
"""

import datetime as dt

from django.contrib.auth import get_user_model
from django.test import TestCase

from .. import confirm, registry
from ..models import PendingAction
from . import _fixtures


def _mk_user(phone):
    return get_user_model().objects.create_user(phone=phone, password='x', name='Mijoz')


class BookingFlowTests(TestCase):
    def setUp(self):
        from booking.models import Venue, VenueService, VenueStaff
        self.user = _mk_user('998914000001')
        owner = _mk_user('998914000002')
        self.venue = Venue.objects.create(
            owner=owner, name='Zamon Sartaroshxona', venue_type='barber',
            is_active=True, prepay_required=False,
            working_hours_start=dt.time(9, 0), working_hours_end=dt.time(20, 0))
        self.soch = VenueService.objects.create(
            venue=self.venue, name='Soch olish', price=30000, duration_minutes=30)
        VenueService.objects.create(
            venue=self.venue, name='Soch + soqol', price=45000, duration_minutes=45)
        self.usta = VenueStaff.objects.create(venue=self.venue, name='Aziz aka',
                                              specialty='Sartarosh')
        self.ctx = _fixtures.user_ctx(self.user, session_key='book')

    def test_find_venue_by_type(self):
        res = registry.dispatch('booking', 'find_venue',
                                {'venue_type': 'barber'}, self.ctx)
        self.assertTrue(res['ok'])
        self.assertEqual(res['ui']['type'], 'card_list')
        self.assertIn('Zamon Sartaroshxona',
                      [it['title'] for it in res['ui']['items']])

    def test_list_services_and_slot_written(self):
        res = registry.dispatch('booking', 'list_services',
                                {'venue_id': str(self.venue.pk)}, self.ctx)
        self.assertEqual(res['ui']['type'], 'product_grid')
        titles = [it['title'] for it in res['ui']['items']]
        self.assertIn('Soch olish', titles)
        # venue_id slot'ga yozildi (ko'p qadamli oqim uchun) — bitta faol vazifa
        from ..models import AgentTask
        tasks = AgentTask.objects.filter(user=self.user, status='active')
        self.assertEqual(tasks.count(), 1)   # BITTA vazifa (slotlar bo'linmasin)
        self.assertEqual(tasks.first().slots.get('venue_id'), str(self.venue.pk))

    def test_available_slots(self):
        res = registry.dispatch('booking', 'available_slots',
                                {'venue_id': str(self.venue.pk), 'day': 'ertaga'},
                                self.ctx)
        self.assertEqual(res['ui']['type'], 'card_list')
        self.assertTrue(res['ui']['items'])
        self.assertIn(':', res['ui']['items'][0]['title'])   # HH:MM

    def test_propose_then_confirm_creates_booking(self):
        from booking.models import VenueBooking
        res = registry.dispatch('booking', 'propose_booking', {
            'venue_id': str(self.venue.pk), 'service_id': str(self.soch.pk),
            'time': '10:00', 'day': 'ertaga'}, self.ctx)
        self.assertEqual(res['result_status'], 'pending')
        self.assertEqual(res['ui']['type'], 'confirm_payment')
        self.assertEqual(res['ui']['total'], 30000)
        # Bron HALI yaratilmagan
        self.assertEqual(VenueBooking.objects.count(), 0)

        out = confirm.execute(res['pending_id'], self.user)
        self.assertTrue(out['ok'])
        self.assertEqual(VenueBooking.objects.count(), 1)
        b = VenueBooking.objects.first()
        self.assertEqual(b.venue_id, self.venue.pk)
        self.assertEqual(b.service_id, self.soch.pk)
        self.assertEqual(b.total_amount, 30000)
        self.assertEqual(b.start_time, dt.time(10, 0))
        self.assertEqual(b.status, 'pending')

    def test_no_confirm_no_booking(self):
        from booking.models import VenueBooking
        registry.dispatch('booking', 'propose_booking', {
            'venue_id': str(self.venue.pk), 'service_id': str(self.soch.pk),
            'time': '11:00', 'day': 'ertaga'}, self.ctx)
        # Tasdiqlanmadi — bron YO'Q
        self.assertEqual(VenueBooking.objects.count(), 0)
        self.assertEqual(PendingAction.objects.filter(user=self.user).count(), 1)

    def test_double_confirm_one_booking(self):
        from booking.models import VenueBooking
        res = registry.dispatch('booking', 'propose_booking', {
            'venue_id': str(self.venue.pk), 'service_id': str(self.soch.pk),
            'time': '12:00', 'day': 'ertaga'}, self.ctx)
        confirm.execute(res['pending_id'], self.user)
        confirm.execute(res['pending_id'], self.user)
        self.assertEqual(VenueBooking.objects.count(), 1)   # idempotent

    def test_anonymous_cannot_propose(self):
        res = registry.dispatch('booking', 'propose_booking', {
            'venue_id': str(self.venue.pk), 'service_id': str(self.soch.pk),
            'time': '13:00', 'day': 'ertaga'}, _fixtures.anon_ctx())
        self.assertFalse(res['ok'])
        self.assertEqual(res['result_status'], 'denied')
        from booking.models import VenueBooking
        self.assertEqual(VenueBooking.objects.count(), 0)

    def test_prepay_venue_sets_prepay(self):
        self.venue.prepay_required = True
        self.venue.save(update_fields=['prepay_required'])
        res = registry.dispatch('booking', 'propose_booking', {
            'venue_id': str(self.venue.pk), 'service_id': str(self.soch.pk),
            'time': '14:00', 'day': 'ertaga', 'payment_method': 'cash'}, self.ctx)
        # prepay_required=True → to'lov usuli 'oldindan'ga majburlanadi
        self.assertIn("oldindan", res['ui']['note'].lower())


class PrefixedIdTests(TestCase):
    """Model kartaning prefiksli id'sini («venue:abc») yuborsa ham tool ishlaydi."""

    def setUp(self):
        from booking.models import Venue, VenueService
        self.user = _mk_user('998914400001')
        owner = _mk_user('998914400002')
        self.venue = Venue.objects.create(
            owner=owner, name='Zamon', venue_type='barber', is_active=True,
            working_hours_start=dt.time(9, 0), working_hours_end=dt.time(20, 0))
        self.svc = VenueService.objects.create(
            venue=self.venue, name='Soch olish', price=30000, duration_minutes=30)
        self.ctx = _fixtures.user_ctx(self.user, session_key='prefix')

    def test_bare_strips_prefix(self):
        from ..tools.booking import _bare
        self.assertEqual(_bare(f'venue:{self.venue.pk}'), str(self.venue.pk))
        self.assertEqual(_bare(str(self.venue.pk)), str(self.venue.pk))
        self.assertEqual(_bare('service:9'), '9')

    def test_list_services_accepts_prefixed_venue_id(self):
        res = registry.dispatch('booking', 'list_services',
                                {'venue_id': f'venue:{self.venue.pk}'}, self.ctx)
        self.assertTrue(res['ok'])
        self.assertNotEqual(res.get('result_status'), 'error')  # ilgari error edi
        self.assertEqual(res['ui']['type'], 'product_grid')


class TimeParseTests(TestCase):
    """Muammo 3 — tabiiy vaqtни tushunish."""

    def test_hour_only_daytime(self):
        from ..tools.booking import _parse_time
        self.assertEqual(_parse_time('11 da'), '11:00')
        self.assertEqual(_parse_time('3 da'), '15:00')      # 1–8 → kunduzги
        self.assertEqual(_parse_time('8 da'), '20:00')
        self.assertEqual(_parse_time('soat 10'), '10:00')

    def test_explicit_minutes_kept(self):
        from ..tools.booking import _parse_time
        self.assertEqual(_parse_time('11:30'), '11:30')
        self.assertEqual(_parse_time('14:30'), '14:30')
        self.assertEqual(_parse_time('soat 14:30 da'), '14:30')

    def test_evening_hint(self):
        from ..tools.booking import _parse_time
        self.assertEqual(_parse_time('kechqurun 7 da'), '19:00')

    def test_unparseable(self):
        from ..tools.booking import _parse_time
        self.assertIsNone(_parse_time('allamahal'))
        self.assertIsNone(_parse_time(''))

    def test_day_with_time_string(self):
        from django.utils import timezone
        from ..tools.booking import _parse_day
        tomorrow = timezone.localdate() + dt.timedelta(days=1)
        self.assertEqual(_parse_day('ertaga soat 3 da'), tomorrow)
        self.assertEqual(_parse_day('11 da'), timezone.localdate())  # faqat vaqt → bugun


class SingleOptionAutoSelectTests(TestCase):
    """Muammo 2 — bitta variant bo'lsa o'zi tanlaydi, «tanlang» demaydi."""

    def setUp(self):
        from booking.models import Venue, VenueService
        self.user = _mk_user('998914100001')
        owner = _mk_user('998914100002')
        self.venue = Venue.objects.create(
            owner=owner, name='Yagona Sartaroshxona', venue_type='barber',
            is_active=True, working_hours_start=dt.time(9, 0),
            working_hours_end=dt.time(20, 0))
        self.svc = VenueService.objects.create(
            venue=self.venue, name='Soch olish', price=30000, duration_minutes=30)
        self.ctx = _fixtures.user_ctx(self.user, session_key='single')

    def test_single_venue_auto_selected(self):
        res = registry.dispatch('booking', 'find_venue', {'venue_type': 'barber'}, self.ctx)
        # «tanlang» EMAS — keyingi qadam (xizmat) so'raladi
        self.assertNotIn('qaysi biridan', res['speech'].lower())
        self.assertIn('xizmat', res['speech'].lower())
        from ..models import AgentTask
        t = AgentTask.objects.get(user=self.user, status='active')
        self.assertEqual(t.slots.get('venue_id'), str(self.venue.pk))

    def test_single_service_auto_selected(self):
        res = registry.dispatch('booking', 'list_services',
                                {'venue_id': str(self.venue.pk)}, self.ctx)
        self.assertIn('tanlandi', res['speech'].lower())
        from ..models import AgentTask
        t = AgentTask.objects.get(user=self.user, status='active')
        self.assertEqual(t.slots.get('service_id'), str(self.svc.pk))

    def test_two_venues_still_asks(self):
        from booking.models import Venue
        Venue.objects.create(owner=self.venue.owner, name='Ikkinchi Barber',
                             venue_type='barber', is_active=True,
                             working_hours_start=dt.time(9, 0),
                             working_hours_end=dt.time(20, 0))
        res = registry.dispatch('booking', 'find_venue', {'venue_type': 'barber'}, self.ctx)
        self.assertIn('qaysi biridan', res['speech'].lower())


class BookingNextStepTests(TestCase):
    """Muammo 1B — [FAOL VAZIFA] keyingi qadamни aniq ko'rsatadi."""

    def setUp(self):
        from .. import task as task_mod
        self.user = _mk_user('998914200001')
        self.ctx = _fixtures.user_ctx(self.user, session_key='nextstep')
        self.task = task_mod.get_or_create_active(self.ctx, goal='booking')

    def _ctxt(self):
        from .. import prompts
        return prompts.build_trusted_context(self.ctx, self.task)

    def test_no_venue_asks_venue(self):
        blob = self._ctxt()
        self.assertIn('[FAOL VAZIFA]', blob)
        self.assertIn('find_venue', blob)

    def test_after_venue_asks_service(self):
        self.task.set_slot('venue_id', '5'); self.task.save()
        blob = self._ctxt()
        self.assertIn('list_services', blob)
        self.assertIn('joy_id=5', blob)

    def test_after_service_asks_time(self):
        self.task.slots = {'venue_id': '5', 'service_id': '9'}; self.task.save()
        blob = self._ctxt()
        self.assertIn('available_slots', blob)

    def test_after_time_asks_confirm(self):
        self.task.slots = {'venue_id': '5', 'service_id': '9', 'time': '11:00'}
        self.task.save()
        blob = self._ctxt()
        self.assertIn('propose_booking', blob)


class ProposeBookingTimeTests(TestCase):
    """propose_booking tabiiy vaqtни qabul qiladi va bandlikni tekshiradi."""

    def setUp(self):
        from booking.models import Venue, VenueService
        self.user = _mk_user('998914300001')
        owner = _mk_user('998914300002')
        self.venue = Venue.objects.create(
            owner=owner, name='Zamon', venue_type='barber', is_active=True,
            prepay_required=False, working_hours_start=dt.time(9, 0),
            working_hours_end=dt.time(20, 0))
        self.svc = VenueService.objects.create(
            venue=self.venue, name='Soch olish', price=30000, duration_minutes=30)
        self.ctx = _fixtures.user_ctx(self.user, session_key='ptime')

    def test_natural_time_accepted(self):
        res = registry.dispatch('booking', 'propose_booking', {
            'venue_id': str(self.venue.pk), 'service_id': str(self.svc.pk),
            'time': '11 da', 'day': 'ertaga'}, self.ctx)
        self.assertEqual(res['result_status'], 'pending')
        self.assertEqual(res['ui']['total'], 30000)

    def test_out_of_hours_polite(self):
        res = registry.dispatch('booking', 'propose_booking', {
            'venue_id': str(self.venue.pk), 'service_id': str(self.svc.pk),
            'time': '23:00', 'day': 'ertaga'}, self.ctx)
        self.assertFalse(res['ok'])
        self.assertEqual(PendingAction.objects.count(), 0)   # bron tayyorlanmaydi
        self.assertIn("bo'sh", res['speech'].lower())


class BookingSchemaTests(TestCase):
    def test_booking_section_in_llm_tools(self):
        fns = {t['function']['name'] for t in registry.build_llm_tools()}
        self.assertIn('booking', fns)

    def test_booking_actions_present(self):
        fn = [t['function'] for t in registry.build_llm_tools()
              if t['function']['name'] == 'booking'][0]
        actions = fn['parameters']['properties']['action']['enum']
        for a in ('find_venue', 'list_services', 'available_slots', 'propose_booking'):
            self.assertIn(a, actions)
