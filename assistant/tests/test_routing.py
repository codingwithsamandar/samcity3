"""PROMPT_9 — engine harakat niyatида chekinadi, agentни soya qilmaydi.

Ildiz: engine.handle() «soch oldirish uchun bron qil» ni category='barber' deб
ushlab, nearest_place (MANZIL) qaytarardi → agent (booking) ISHLAMASdi.
Yechim: harakat niyati bo'lsa engine 'unknown' qaytaradi → service agentга uzatadi.

⚠️ Diskriminator: «eng yaqin sartaroshxona» (manzil) o'zgarmaydi; «bron qil»
(amal) chekinadi; «qanday bron qilaman» (HOW-TO) chekinmasdan KB'ga o'tadi.
"""

from unittest import mock

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.contrib.auth.models import AnonymousUser

from .. import engine, service


def _mk_user(phone):
    return get_user_model().objects.create_user(phone=phone, password='x', name='T')


class ActionIntentDetectTests(TestCase):
    def test_action_intents(self):
        for msg in ('sartaroshxonadan joy bron qil',
                    'menga soch oldirish uchun joy bron qil',
                    'soch oldirmoqchiman',
                    'lavash buyurtma qil',
                    'restorandan ovqat buyurtma qil',
                    'ertaga soat 3 ga yozib qoy',
                    'zal bron qilish'):
            self.assertTrue(engine.is_action_intent(msg), msg)

    def test_not_action_address_queries(self):
        for msg in ('eng yaqin sartaroshxona',
                    'sartaroshxona qayerda',
                    'eng yaqin restoran',
                    'eng yaqin dorixona'):
            self.assertFalse(engine.is_action_intent(msg), msg)

    def test_howto_not_action(self):
        # «qanday bron qilaman» — ma'lumot so'rovi, amal EMAS → KB javob beradi
        self.assertFalse(engine.is_action_intent("to'yxona qanday bron qilaman"))
        self.assertFalse(engine.is_action_intent("qanday buyurtma beraman"))


class EngineRetreatTests(TestCase):
    def setUp(self):
        from places.models import Place
        # barber toifasида joylar — engine ular bilan «bron»ни shadow qilmasin
        Place.objects.create(name='Zamon Barber', category='barber',
                             latitude=engine.CENTER[0], longitude=engine.CENTER[1])

    def test_barber_booking_action_unknown(self):
        res = engine.handle('menga soch oldirish uchun joy bron qil')
        self.assertEqual(res['intent'], 'unknown')

    def test_barber_bron_unknown(self):
        self.assertEqual(engine.handle('sartaroshxonadan joy bron qil')['intent'],
                         'unknown')

    def test_barber_address_still_works(self):
        # Harakatsiz — engine MANZIL beradi (o'zgarmaydi)
        res = engine.handle('eng yaqin sartaroshxona')
        self.assertEqual(res['intent'], 'nearest_place')
        self.assertEqual(res['category'], 'barber')

    def test_delivery_order_action_unknown(self):
        self.assertEqual(engine.handle('restorandan ovqat buyurtma qil')['intent'],
                         'unknown')

    def test_salesman_job_not_ads(self):
        """«sotuvchi ishi bormi» — ish qidiruvи, e'lon EMAS (engine 'sotuv' xatosi)."""
        res = engine.handle('sotuvchi ishi bormi')
        self.assertNotEqual(res['intent'], 'ads')     # → unknown → agent (jobs)

    def test_buy_stays_ads_search(self):
        """«sotib olaman» — e'lon qidiruvи (engine'да qoladi)."""
        res = engine.handle('mashina sotib olaman')
        self.assertEqual(res['intent'], 'ads')

    def test_restaurant_address_still_works(self):
        from places.models import Place
        Place.objects.create(name='Osh Markazi', category='restaurant',
                             latitude=engine.CENTER[0], longitude=engine.CENTER[1])
        res = engine.handle('eng yaqin restoran')
        self.assertEqual(res['intent'], 'nearest_place')


class ServiceRoutingTests(TestCase):
    """service.build_response: kirgan user + harakat niyati → agent chaqiriladi."""

    def _req(self, user):
        req = RequestFactory().post('/ai/chat/')
        req.user = user
        return req

    def test_authenticated_action_reaches_agent(self):
        user = _mk_user('998915000001')
        fake = {'ok': True, 'reply': 'Qaysi xizmat kerak?', 'ui': {'type': 'card_list'},
                'intent': 'agent', 'source': 'agent'}
        with mock.patch('assistant.service._try_agent', return_value=fake) as m:
            res = service.build_response('menga soch oldirish uchun joy bron qil',
                                         request=self._req(user))
        m.assert_called_once()
        self.assertEqual(res['intent'], 'agent')
        self.assertEqual(res['ui']['type'], 'card_list')

    def test_authenticated_address_stays_engine(self):
        """Harakatsiz «eng yaqin sartaroshxona» — agent chaqirilmaydi, engine javob."""
        from places.models import Place
        Place.objects.create(name='Zamon Barber', category='barber',
                             latitude=engine.CENTER[0], longitude=engine.CENTER[1])
        user = _mk_user('998915000002')
        with mock.patch('assistant.service._try_agent') as m:
            res = service.build_response('eng yaqin sartaroshxona',
                                         request=self._req(user))
        m.assert_not_called()
        self.assertEqual(res['intent'], 'nearest_place')

    def test_anonymous_action_says_login(self):
        req = RequestFactory().post('/ai/chat/')
        req.user = AnonymousUser()
        with mock.patch.object(service.llm, 'ask') as ask:
            res = service.build_response('sartaroshxonadan joy bron qil', request=req)
        ask.assert_not_called()               # anonim → LLM ga bormaydi
        self.assertIn('tizimga kiring', res['reply'].lower())
        self.assertTrue(any('Kirish' in a.get('label', '') for a in res.get('actions', [])))


class SectionRetreatTests(TestCase):
    """Engine agent-egallagan bo'lim intent'larини (delivery/ads/jobs/booking/taxi)
    kirgan foydalanuvchi uchun agentга uzatadi — engine ularни SHADOW qilmasin."""

    def _req(self, user):
        from django.contrib.sessions.backends.db import SessionStore
        req = RequestFactory().post('/ai/chat/')
        req.user = user
        s = SessionStore(); s.create(); req.session = s
        return req

    def _agent(self, reply='ok'):
        return {'ok': True, 'reply': reply, 'ui': {'type': 'link_list'},
                'intent': 'agent', 'source': 'agent'}

    def test_ad_search_goes_to_agent(self):
        from main.models import Ad
        user = _mk_user('998922000001')
        Ad.objects.create(user=user, category='avtomobil', title='Nexia', status='active')
        with mock.patch('assistant.service._try_agent', return_value=self._agent()) as m:
            res = service.build_response('mashina sotiladigan e\'lonlar bormi',
                                         request=self._req(user))
        m.assert_called_once()
        self.assertEqual(res['intent'], 'agent')

    def test_cart_query_goes_to_agent(self):
        user = _mk_user('998922000002')
        with mock.patch('assistant.service._try_agent', return_value=self._agent()) as m:
            res = service.build_response('savatimда nima bor', request=self._req(user))
        m.assert_called_once()
        self.assertEqual(res['intent'], 'agent')

    def test_community_query_goes_to_agent(self):
        user = _mk_user('998922000003')
        with mock.patch('assistant.service._try_agent', return_value=self._agent()) as m:
            res = service.build_response('mahallamда yo\'l buzuq, murojaat yubormoqchiman',
                                         request=self._req(user))
        m.assert_called_once()

    def test_agent_none_falls_back_to_engine(self):
        """No-key: agent None → engine natijasi saqlanadi (uzilmaydi)."""
        from main.models import Ad
        user = _mk_user('998922000004')
        Ad.objects.create(user=user, category='avtomobil', title='Mashina sotiladi',
                          status='active', contact_phone='998900000000')
        with mock.patch('assistant.service._try_agent', return_value=None):
            res = service.build_response('mashina sotib olaman', request=self._req(user))
        self.assertEqual(res['intent'], 'ads')        # engine natijasи (zaxira)
        self.assertEqual(res['source'], 'local')
        self.assertTrue(res['cards'])

    def test_places_stays_engine(self):
        """places (manzil) — agentга UZATILMAYDI, engine bepul javob beradi."""
        from places.models import Place
        Place.objects.create(name='Dorixona', category='pharmacy',
                             latitude=engine.CENTER[0], longitude=engine.CENTER[1])
        user = _mk_user('998922000005')
        with mock.patch('assistant.service._try_agent') as m:
            res = service.build_response('eng yaqin dorixona', request=self._req(user))
        m.assert_not_called()
        self.assertEqual(res['intent'], 'nearest_place')

    def test_community_detect(self):
        self.assertTrue(engine.is_community_query('murojaat yubormoqchiman'))
        self.assertTrue(engine.is_community_query('mahallamda qanday e\'lonlar bor'))
        self.assertTrue(engine.is_community_query('so\'rovnomaga ovoz bermoqchiman'))
        self.assertFalse(engine.is_community_query('eng yaqin dorixona'))
        self.assertFalse(engine.is_community_query('e\'lon joylash'))   # ads, mahalla emas
