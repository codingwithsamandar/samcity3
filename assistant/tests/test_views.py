"""HTTP endpoint testlari — /ai/confirm/ va /ai/cancel/ (web + CSRF + egalik)."""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from .. import registry
from ..models import PendingAction
from . import _fixtures


def _mk_user(phone):
    return get_user_model().objects.create_user(phone=phone, password='x', name='Test')


class ConfirmEndpointTests(TestCase):
    def setUp(self):
        cache.clear()
        _fixtures.EXEC_COUNT['buy'] = 0
        self.user = _mk_user('998904000001')
        self.other = _mk_user('998904000002')
        res = registry.dispatch('delivery', 't_buy', {'amount': 4000},
                                _fixtures.user_ctx(self.user))
        self.pid = res['pending_id']

    def test_anonymous_gets_404(self):
        c = Client()
        resp = c.post(reverse('assistant:confirm', args=[self.pid]))
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(_fixtures.EXEC_COUNT['buy'], 0)

    def test_owner_confirms(self):
        c = Client()
        c.force_login(self.user)
        resp = c.post(reverse('assistant:confirm', args=[self.pid]))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['ok'])
        self.assertEqual(_fixtures.EXEC_COUNT['buy'], 1)
        self.assertEqual(PendingAction.objects.get(id=self.pid).status, 'confirmed')

    def test_other_user_404(self):
        c = Client()
        c.force_login(self.other)
        resp = c.post(reverse('assistant:confirm', args=[self.pid]))
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(_fixtures.EXEC_COUNT['buy'], 0)

    def test_double_confirm_http_idempotent(self):
        c = Client()
        c.force_login(self.user)
        r1 = c.post(reverse('assistant:confirm', args=[self.pid]))
        r2 = c.post(reverse('assistant:confirm', args=[self.pid]))
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(_fixtures.EXEC_COUNT['buy'], 1)  # bitta bajarish

    def test_cancel_then_confirm_conflict(self):
        c = Client()
        c.force_login(self.user)
        cancel = c.post(reverse('assistant:cancel', args=[self.pid]))
        self.assertEqual(cancel.status_code, 200)
        confirm = c.post(reverse('assistant:confirm', args=[self.pid]))
        self.assertEqual(confirm.status_code, 409)
        self.assertEqual(_fixtures.EXEC_COUNT['buy'], 0)

    def test_get_not_allowed(self):
        c = Client()
        c.force_login(self.user)
        resp = c.get(reverse('assistant:confirm', args=[self.pid]))
        self.assertEqual(resp.status_code, 405)


class CsrfTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = _mk_user('998904000010')
        res = registry.dispatch('delivery', 't_buy', {'amount': 1000},
                                _fixtures.user_ctx(self.user))
        self.pid = res['pending_id']

    def test_csrf_required_for_session_web(self):
        # CSRF majburiy — token bo'lmasa 403 (sessiyali web himoyasi)
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.user)
        resp = c.post(reverse('assistant:confirm', args=[self.pid]))
        self.assertEqual(resp.status_code, 403)
