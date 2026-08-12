"""A1 — anonim foydalanuvchi LLM ga UMUMAN bormaydi (xarajat kafolati).

Chat endpoint'i ochiq. Kirmagan odam engine.py bilan to'liq ishlaydi, lekin
na agent, na oddiy llm.ask chaqiriladi — 0 so'm.
"""

from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from .. import agent, service
from . import _fixtures


def _mk_user(phone):
    return get_user_model().objects.create_user(phone=phone, password='x', name='Test')


class AnonAgentBlockedTests(TestCase):
    def test_anonymous_agent_returns_none_without_calling_llm(self):
        call_mock = mock.Mock()
        with mock.patch.object(agent.llm, 'agent_enabled', return_value=True), \
             mock.patch.object(agent.llm, 'call', call_mock):
            res = agent.run("lavash buyurtma qil", _fixtures.anon_ctx(session_key='s1'))
        self.assertIsNone(res)
        call_mock.assert_not_called()   # ← LLM UMUMAN chaqirilmadi

    def test_authenticated_agent_still_works(self):
        user = _mk_user('998905000001')
        call_mock = mock.Mock(return_value={'content': 'Salom!', 'tool_calls': [],
                                            'usage': {}})
        with mock.patch.object(agent.llm, 'agent_enabled', return_value=True), \
             mock.patch.object(agent.llm, 'call', call_mock):
            res = agent.run("salom", _fixtures.user_ctx(user))
        self.assertIsNotNone(res)
        self.assertEqual(res['reply'], 'Salom!')
        call_mock.assert_called_once()


class AnonServiceTests(TestCase):
    """service.build_response anonim uchun LLM ga bormaydi, muloyim taklif beradi."""

    def setUp(self):
        cache.clear()

    def _anon_request(self):
        from django.contrib.auth.models import AnonymousUser
        from django.test import RequestFactory
        req = RequestFactory().post('/ai/chat/')
        req.user = AnonymousUser()
        return req

    def test_anon_unknown_query_never_calls_llm(self):
        ask_mock = mock.Mock()
        with mock.patch.object(service.llm, 'ask', ask_mock):
            res = service.build_response("kvant fizikasi haqida gapir",
                                         request=self._anon_request())
        ask_mock.assert_not_called()        # ← oddiy llm.ask ham chaqirilmadi
        self.assertEqual(res['intent'], 'fallback')
        self.assertTrue(res['ok'])

    def test_anon_fallback_suggests_login(self):
        res = service.build_response("kvant fizikasi haqida gapir",
                                     request=self._anon_request())
        self.assertIn('tizimga kirsangiz', res['reply'].lower())
        # Kirish havolasi birinchi tugma bo'lsin
        self.assertTrue(res['actions'])
        self.assertIn('Kirish', res['actions'][0]['label'])

    def test_anon_engine_answers_still_work(self):
        """Anonim uchun mahalliy dvigatel BUZILMAYDI — joy topish ishlayveradi."""
        from places.models import Place
        from .. import engine
        Place.objects.create(name="Dorixona Shifo", category='pharmacy',
                             latitude=engine.CENTER[0], longitude=engine.CENTER[1])
        res = service.build_response("eng yaqin dorixona", request=self._anon_request())
        self.assertEqual(res['intent'], 'nearest_place')
        self.assertTrue(res['cards'])

    def test_anon_chat_endpoint_ok(self):
        c = Client()
        resp = c.post(reverse('assistant:chat'),
                      data='{"message": "salom"}',
                      content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['ok'])


class AuthenticatedNotBlockedTests(TestCase):
    """Kirgan foydalanuvchida eski oqim (llm.ask fallback) saqlanadi."""

    def setUp(self):
        cache.clear()
        self.user = _mk_user('998905000010')

    def _auth_request(self):
        from django.test import RequestFactory
        req = RequestFactory().post('/ai/chat/')
        req.user = self.user
        return req

    def test_authenticated_reaches_llm_ask(self):
        with mock.patch.object(service.llm, 'ask', return_value='LLM javobi'):
            res = service.build_response("kvant fizikasi haqida gapir",
                                         request=self._auth_request())
        self.assertEqual(res['intent'], 'llm')
        self.assertEqual(res['reply'], 'LLM javobi')

    def test_no_request_keeps_legacy_behaviour(self):
        """request berilmasa (eski chaqiruv) — kimligini bilmaymiz, llm.ask ishlaydi."""
        with mock.patch.object(service.llm, 'ask', return_value='Eski oqim'):
            res = service.build_response("kvant fizikasi haqida gapir")
        self.assertEqual(res['intent'], 'llm')
