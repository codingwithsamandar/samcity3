"""PROMPT_10 — faol vazifa bo'lsa engine chekinadi (suhbat o'rtasида uzilmasin).

Ildiz: bron davom etayotган bo'lsa ham, «soch olish» (harakat so'zisiz, lekin
`soch`=barber toifasi) engine tomonidан ushlanib, agent soya qilinardi → suhbat
uzilardi. Yechim: faol AgentTask bo'lsa, service engine'ni CHETLAB agentga o'tadi.
"""

from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from .. import service, task as task_mod
from .. import engine
from ..registry import ToolContext


def _mk_user(phone):
    return get_user_model().objects.create_user(phone=phone, password='x', name='T')


class ActiveTaskBypassTests(TestCase):
    def setUp(self):
        self.user = _mk_user('998916000001')
        self.req = RequestFactory().post('/ai/chat/')
        self.req.user = self.user
        # Sessiya kaliti — build_context session_key ni o'qiydi
        from django.contrib.sessions.backends.db import SessionStore
        s = SessionStore(); s.create()
        self.req.session = s
        # Faol booking vazifasi (bron davom etyapti)
        self.ctx = ToolContext(user=self.user, session_key=s.session_key)
        task_mod.get_or_create_active(self.ctx, goal='booking')

    def _agent_ok(self, reply='Qaysi vaqtga yozilasiz?'):
        return {'ok': True, 'reply': reply, 'ui': {'type': 'card_list'},
                'intent': 'agent', 'source': 'agent'}

    def test_short_reply_goes_to_agent_not_engine(self):
        """«soch olish» — faol vazifa bor → agent (engine MANZIL bermaydi)."""
        with mock.patch('assistant.service._try_agent', return_value=self._agent_ok()) as m, \
             mock.patch('assistant.service.engine.handle') as eng:
            res = service.build_response('soch olish', request=self.req)
        m.assert_called_once()
        eng.assert_not_called()               # engine UMUMAN chaqirilmadi
        self.assertEqual(res['intent'], 'agent')
        self.assertEqual(res['ui']['type'], 'card_list')

    def test_time_reply_goes_to_agent(self):
        with mock.patch('assistant.service._try_agent',
                        return_value=self._agent_ok('Tasdiqlaysizmi?')) as m:
            res = service.build_response('11 da', request=self.req)
        m.assert_called_once()
        self.assertEqual(res['reply'], 'Tasdiqlaysizmi?')

    def test_agent_none_falls_back_to_engine(self):
        """Agent ishlamasa (LLM down) — engine'ga tushib, uzilmasin (zaxira)."""
        with mock.patch('assistant.service._try_agent', return_value=None):
            res = service.build_response('eng yaqin dorixona', request=self.req)
        # engine javob berdi (agent None) — uzilmadi
        self.assertNotEqual(res.get('intent'), 'agent')

    def test_done_task_returns_to_engine_fastpath(self):
        """Vazifa tugagach (done) — keyingi xabar yana engine fast-path'ga tushadi."""
        from ..models import AgentTask
        AgentTask.objects.filter(user=self.user).update(status='done')
        from places.models import Place
        Place.objects.create(name='Dorixona', category='pharmacy',
                             latitude=engine.CENTER[0], longitude=engine.CENTER[1])
        with mock.patch('assistant.service._try_agent') as m:
            res = service.build_response('eng yaqin dorixona', request=self.req)
        m.assert_not_called()                 # agent chaqirilmadi
        self.assertEqual(res['intent'], 'nearest_place')


class NoActiveTaskTests(TestCase):
    """Vazifasiz holatда engine fast-path o'zgarmaydi (bepul so'rovlar qoladi)."""

    def setUp(self):
        from places.models import Place
        self.user = _mk_user('998916000010')
        self.req = RequestFactory().post('/ai/chat/')
        self.req.user = self.user
        from django.contrib.sessions.backends.db import SessionStore
        s = SessionStore(); s.create()
        self.req.session = s
        Place.objects.create(name='Dorixona', category='pharmacy',
                             latitude=engine.CENTER[0], longitude=engine.CENTER[1])

    def test_no_task_engine_fastpath(self):
        with mock.patch('assistant.service._try_agent') as m:
            res = service.build_response('eng yaqin dorixona', request=self.req)
        m.assert_not_called()                 # vazifa yo'q → agent chaqirilmaydi
        self.assertEqual(res['intent'], 'nearest_place')


class AnonymousActiveTaskTests(TestCase):
    """Anonim — agent o'chiq, faol vazifa bo'lsa ham engine (o'zgarmaydi)."""

    def test_anon_stays_engine(self):
        from places.models import Place
        Place.objects.create(name='Dorixona', category='pharmacy',
                             latitude=engine.CENTER[0], longitude=engine.CENTER[1])
        req = RequestFactory().post('/ai/chat/')
        req.user = AnonymousUser()
        with mock.patch('assistant.service._has_active_task') as ht, \
             mock.patch('assistant.service._try_agent') as m:
            res = service.build_response('eng yaqin dorixona', request=req)
        m.assert_not_called()
        ht.assert_not_called()                # anonim — vazifa ham tekshirilmaydi
        self.assertEqual(res['intent'], 'nearest_place')
