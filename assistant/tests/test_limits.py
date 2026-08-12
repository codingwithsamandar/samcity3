"""A2 — `proposals` (taklif) va `mutations` (bajarilgan) alohida hisoblanadi.

Asosiy stsenariy: ko'p taklif qilib, hech birini tasdiqlamagan foydalanuvchi
bloklanmasligi kerak — bu avvalgi xatolik edi.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .. import confirm, guard, registry
from ..models import AgentUsage
from . import _fixtures


def _mk_user(phone):
    return get_user_model().objects.create_user(phone=phone, password='x', name='Test')


def _usage(user, **fields):
    return AgentUsage.objects.create(user=user, date=timezone.localdate(), **fields)


class ProposalLimitTests(TestCase):
    def setUp(self):
        _fixtures.EXEC_COUNT['buy'] = 0
        self.user = _mk_user('998906000001')
        self.ctx = _fixtures.user_ctx(self.user)

    def test_proposal_increments_proposals_not_mutations(self):
        registry.dispatch('delivery', 't_buy', {'amount': 1000}, self.ctx)
        u = AgentUsage.objects.get(user=self.user)
        self.assertEqual(u.proposals, 1)
        self.assertEqual(u.mutations, 0)   # ← hali hech narsa bajarilmadi

    def test_over_proposal_limit_denied(self):
        _usage(self.user, proposals=guard.LIMITS['proposals'])
        res = registry.dispatch('delivery', 't_buy', {'amount': 1000}, self.ctx)
        self.assertFalse(res['ok'])
        self.assertEqual(res['result_status'], 'limited')
        self.assertIn('tasdiqqa', res['reply'].lower())

    def test_under_proposal_limit_allowed(self):
        _usage(self.user, proposals=guard.LIMITS['proposals'] - 1)
        res = registry.dispatch('delivery', 't_buy', {'amount': 1000}, self.ctx)
        self.assertEqual(res['result_status'], 'pending')

    def test_many_proposals_no_confirm_can_still_order(self):
        """ASOSIY STSENARIY: 30 ta taklif + 0 tasdiq → hali ham buyurtma qila oladi."""
        _usage(self.user, proposals=30, mutations=0)
        res = registry.dispatch('delivery', 't_buy', {'amount': 1000}, self.ctx)
        self.assertEqual(res['result_status'], 'pending')
        out = confirm.execute(res['pending_id'], self.user)
        self.assertTrue(out['ok'])
        self.assertEqual(_fixtures.EXEC_COUNT['buy'], 1)


class MutationLimitTests(TestCase):
    def setUp(self):
        _fixtures.EXEC_COUNT['buy'] = 0
        self.user = _mk_user('998906000010')
        self.ctx = _fixtures.user_ctx(self.user)

    def test_confirm_increments_mutations(self):
        res = registry.dispatch('delivery', 't_buy', {'amount': 1000}, self.ctx)
        confirm.execute(res['pending_id'], self.user)
        u = AgentUsage.objects.get(user=self.user)
        self.assertEqual(u.mutations, 1)
        self.assertEqual(u.proposals, 1)

    def test_over_mutation_limit_blocks_execution(self):
        res = registry.dispatch('delivery', 't_buy', {'amount': 1000}, self.ctx)
        # Taklifdan KEYIN limitni to'ldiramiz — tasdiq paytida to'silsin
        AgentUsage.objects.filter(user=self.user).update(
            mutations=guard.LIMITS['mutations'])
        out = confirm.execute(res['pending_id'], self.user)
        self.assertFalse(out['ok'])
        self.assertEqual(out['status'], 429)
        self.assertEqual(_fixtures.EXEC_COUNT['buy'], 0)   # bajarilmadi

    def test_blocked_pending_stays_pending_for_retry(self):
        """Limit tufayli to'silgan amal 'pending' bo'lib qoladi — ertaga urinish mumkin."""
        from ..models import PendingAction
        res = registry.dispatch('delivery', 't_buy', {'amount': 1000}, self.ctx)
        AgentUsage.objects.filter(user=self.user).update(
            mutations=guard.LIMITS['mutations'])
        confirm.execute(res['pending_id'], self.user)
        self.assertEqual(PendingAction.objects.get(id=res['pending_id']).status,
                         'pending')

    def test_idempotent_confirm_counts_mutation_once(self):
        res = registry.dispatch('delivery', 't_buy', {'amount': 1000}, self.ctx)
        confirm.execute(res['pending_id'], self.user)
        confirm.execute(res['pending_id'], self.user)
        u = AgentUsage.objects.get(user=self.user)
        self.assertEqual(u.mutations, 1)   # ikki marta tasdiq — bitta sanoq
        self.assertEqual(_fixtures.EXEC_COUNT['buy'], 1)
