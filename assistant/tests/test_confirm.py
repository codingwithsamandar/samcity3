"""confirm.py + mutating oqim testlari.

Butun xavfsizlik modelining isboti:
  • mutating=True tool HECH QACHON to'g'ridan-to'g'ri bajarmaydi
  • PendingAction yaratiladi, haqiqiy amal faqat tasdiqdan keyin
  • ikki marta tasdiq → bitta bajarish (idempotentlik)
  • muddati o'tgan / boshqa foydalanuvchi → bajarilmaydi
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .. import confirm, registry
from ..models import PendingAction
from . import _fixtures


def _mk_user(phone):
    return get_user_model().objects.create_user(phone=phone, password='x')


class MutatingNeverExecutesTests(TestCase):
    def setUp(self):
        _fixtures.EXEC_COUNT['buy'] = 0
        self.user = _mk_user('998901000001')

    def test_dispatch_creates_pending_not_execution(self):
        res = registry.dispatch('delivery', 't_buy', {'amount': 5000},
                                _fixtures.user_ctx(self.user))
        self.assertEqual(res['result_status'], 'pending')
        self.assertIn('pending_id', res)
        # HECH NARSA bajarilmagan
        self.assertEqual(_fixtures.EXEC_COUNT['buy'], 0)
        # PendingAction yozuvi bor, statusi 'pending'
        pa = PendingAction.objects.get(id=res['pending_id'])
        self.assertEqual(pa.status, 'pending')
        self.assertEqual(int(pa.amount), 5000)

    def test_confirm_then_executes(self):
        res = registry.dispatch('delivery', 't_buy', {'amount': 3000},
                                _fixtures.user_ctx(self.user))
        out = confirm.execute(res['pending_id'], self.user)
        self.assertTrue(out['ok'])
        self.assertEqual(_fixtures.EXEC_COUNT['buy'], 1)
        pa = PendingAction.objects.get(id=res['pending_id'])
        self.assertEqual(pa.status, 'confirmed')
        self.assertIsNotNone(pa.confirmed_at)

    def test_double_confirm_executes_once(self):
        res = registry.dispatch('delivery', 't_buy', {'amount': 3000},
                                _fixtures.user_ctx(self.user))
        pid = res['pending_id']
        first = confirm.execute(pid, self.user)
        second = confirm.execute(pid, self.user)
        self.assertTrue(first['ok'])
        self.assertTrue(second['ok'])
        self.assertTrue(second.get('idempotent'))
        # Ikki marta tasdiq — lekin BITTA bajarish
        self.assertEqual(_fixtures.EXEC_COUNT['buy'], 1)


class PendingGuardTests(TestCase):
    def setUp(self):
        _fixtures.EXEC_COUNT['buy'] = 0
        self.user = _mk_user('998901000010')
        self.other = _mk_user('998901000011')
        res = registry.dispatch('delivery', 't_buy', {'amount': 1000},
                                _fixtures.user_ctx(self.user))
        self.pid = res['pending_id']

    def test_expired_not_executed(self):
        PendingAction.objects.filter(id=self.pid).update(
            expires_at=timezone.now() - timezone.timedelta(minutes=1))
        out = confirm.execute(self.pid, self.user)
        self.assertFalse(out['ok'])
        self.assertEqual(out['status'], 410)
        self.assertEqual(_fixtures.EXEC_COUNT['buy'], 0)
        self.assertEqual(PendingAction.objects.get(id=self.pid).status, 'expired')

    def test_other_user_gets_404(self):
        out = confirm.execute(self.pid, self.other)
        self.assertFalse(out['ok'])
        self.assertEqual(out['status'], 404)
        self.assertEqual(_fixtures.EXEC_COUNT['buy'], 0)
        # Yozuv hali 'pending' (boshqa odam unga tegina olmaydi)
        self.assertEqual(PendingAction.objects.get(id=self.pid).status, 'pending')

    def test_cancel_prevents_execution(self):
        cancel = confirm.cancel(self.pid, self.user)
        self.assertTrue(cancel['ok'])
        out = confirm.execute(self.pid, self.user)
        self.assertFalse(out['ok'])
        self.assertEqual(out['status'], 409)
        self.assertEqual(_fixtures.EXEC_COUNT['buy'], 0)

    def test_cancel_other_user_404(self):
        out = confirm.cancel(self.pid, self.other)
        self.assertFalse(out['ok'])
        self.assertEqual(out['status'], 404)


class AnonymousMutatingTests(TestCase):
    def test_anonymous_cannot_propose(self):
        # mutating tool auth_required — anonim rad etiladi (pending ham yaratilmaydi)
        res = registry.dispatch('delivery', 't_buy', {'amount': 1000},
                                _fixtures.anon_ctx())
        self.assertFalse(res['ok'])
        self.assertEqual(res['result_status'], 'denied')
        self.assertEqual(PendingAction.objects.count(), 0)
