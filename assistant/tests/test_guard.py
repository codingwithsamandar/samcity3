"""guard.py testlari — vakolat, egalik, tuman filtri, kunlik limit, audit."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .. import guard, registry
from ..models import AgentAuditLog, AgentUsage
from . import _fixtures


def _mk_user(phone):
    return get_user_model().objects.create_user(phone=phone, password='x')


class AuthTests(TestCase):
    def test_anonymous_cannot_call_auth_required(self):
        res = registry.dispatch('delivery', 't_secret', {}, _fixtures.anon_ctx())
        self.assertFalse(res['ok'])
        self.assertEqual(res['result_status'], 'denied')

    def test_authenticated_can_call_auth_required(self):
        u = _mk_user('998900000001')
        res = registry.dispatch('delivery', 't_secret', {}, _fixtures.user_ctx(u))
        self.assertTrue(res['ok'])


class OwnershipTests(TestCase):
    def setUp(self):
        from delivery.models import Store
        self.owner = _mk_user('998900000010')
        self.other = _mk_user('998900000011')
        self.store = Store.objects.create(owner=self.owner, name='Egasining doʻkoni')

    def test_owner_passes(self):
        res = registry.dispatch('delivery', 't_owned',
                                {'store_id': self.store.pk}, _fixtures.user_ctx(self.owner))
        self.assertTrue(res['ok'])

    def test_other_user_denied(self):
        res = registry.dispatch('delivery', 't_owned',
                                {'store_id': self.store.pk}, _fixtures.user_ctx(self.other))
        self.assertFalse(res['ok'])
        self.assertEqual(res['result_status'], 'denied')

    def test_nonexistent_id_denied_same_as_foreign(self):
        # Mavjud bo'lmagan ID ham 'denied' (mavjudligini oshkor qilmaymiz)
        res = registry.dispatch('delivery', 't_owned',
                                {'store_id': 999999}, _fixtures.user_ctx(self.owner))
        self.assertFalse(res['ok'])
        self.assertEqual(res['result_status'], 'denied')


class DistrictFilterTests(TestCase):
    def setUp(self):
        from main.models import District, Neighborhood
        from delivery.models import Store
        self.d_a = District.objects.create(name='Tuman A')
        self.d_b = District.objects.create(name='Tuman B')
        nb_a = Neighborhood.objects.create(name='Mahalla A', district=self.d_a)
        nb_b = Neighborhood.objects.create(name='Mahalla B', district=self.d_b)
        owner = _mk_user('998900000020')
        self.store_a = Store.objects.create(owner=owner, name='Do\'kon A',
                                            store_type='mahalla', neighborhood=nb_a)
        self.store_b = Store.objects.create(owner=owner, name='Do\'kon B',
                                            store_type='mahalla', neighborhood=nb_b)

    def test_other_district_store_excluded(self):
        from delivery.models import Store
        ctx = registry.ToolContext(district=self.d_a)
        qs = guard.apply_district(Store.objects.all(), ctx)
        names = set(qs.values_list('name', flat=True))
        self.assertIn("Do'kon A", names)
        self.assertNotIn("Do'kon B", names)

    def test_no_district_returns_all(self):
        from delivery.models import Store
        ctx = registry.ToolContext(district=None)
        qs = guard.apply_district(Store.objects.all(), ctx)
        self.assertEqual(qs.count(), 2)


class DailyLimitTests(TestCase):
    def test_over_tool_limit_is_limited(self):
        u = _mk_user('998900000030')
        AgentUsage.objects.create(user=u, date=timezone.localdate(),
                                  tool_calls=guard.LIMITS['tool_calls'])
        res = registry.dispatch('delivery', 't_echo', {'x': 1}, _fixtures.user_ctx(u))
        self.assertFalse(res['ok'])
        self.assertEqual(res['result_status'], 'limited')

    def test_under_limit_increments_counter(self):
        u = _mk_user('998900000031')
        res = registry.dispatch('delivery', 't_echo', {'x': 1}, _fixtures.user_ctx(u))
        self.assertTrue(res['ok'])
        usage = AgentUsage.objects.get(user=u)
        self.assertEqual(usage.tool_calls, 1)


class AmountLimitTests(TestCase):
    def test_single_amount_over_limit(self):
        u = _mk_user('998900000040')
        ctx = _fixtures.user_ctx(u)
        over = guard.LIMITS['single_amount'] + 1
        self.assertIsNotNone(guard.check_amount(ctx, over))

    def test_daily_amount_accumulates(self):
        u = _mk_user('998900000041')
        ctx = _fixtures.user_ctx(u)
        guard.record_amount(u, guard.LIMITS['daily_amount'] - 100)
        # Yana 200 — kunlik chegaradan oshadi
        self.assertIsNotNone(guard.check_amount(ctx, 200))

    def test_zero_amount_ok(self):
        u = _mk_user('998900000042')
        self.assertIsNone(guard.check_amount(_fixtures.user_ctx(u), 0))


class AuditTests(TestCase):
    def test_every_call_is_audited(self):
        before = AgentAuditLog.objects.count()
        registry.dispatch('delivery', 't_echo', {'x': 1}, _fixtures.anon_ctx())
        registry.dispatch('delivery', 'nope', {}, _fixtures.anon_ctx())
        self.assertEqual(AgentAuditLog.objects.count(), before + 2)

    def test_denied_call_audited_with_status(self):
        registry.dispatch('delivery', 't_secret', {}, _fixtures.anon_ctx())
        log = AgentAuditLog.objects.filter(action='t_secret').latest('created_at')
        self.assertEqual(log.result_status, 'denied')
