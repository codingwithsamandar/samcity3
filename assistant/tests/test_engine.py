"""AI yordamchi — mahalliy dvigatel (engine) uchun testlar.

Bu testlar bazasiz ishlaydigan qismlarni (niyat/toifa aniqlash) va bazaga
tayanadigan qismlarni (eng yaqin joy) qamrab oladi.
"""

import json

from unittest import skipUnless

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, Client
from django.urls import reverse, NoReverseMatch

from .. import engine, knowledge, views
from ..models import UnansweredQuery, record_unanswered


class DetectCategoryTests(TestCase):
    def test_pharmacy_uz(self):
        self.assertEqual(engine.detect_category(engine._norm("eng yaqin dorixona")), 'pharmacy')

    def test_pharmacy_ru(self):
        self.assertEqual(engine.detect_category(engine._norm("где аптека")), 'pharmacy')

    def test_hospital(self):
        self.assertEqual(engine.detect_category(engine._norm("kasalxona qayerda")), 'hospital')

    def test_bank(self):
        self.assertEqual(engine.detect_category(engine._norm("yaqin bank")), 'bank')

    def test_restaurant(self):
        self.assertEqual(engine.detect_category(engine._norm("yaxshi kafe bormi")), 'restaurant')

    def test_apostrophe_variants(self):
        # "to'yxona" har xil apostrof bilan yozilishi mumkin
        self.assertEqual(engine.detect_category(engine._norm("toʻyxona")), 'wedding')
        self.assertEqual(engine.detect_category(engine._norm("to'yxona")), 'wedding')

    def test_no_category(self):
        self.assertIsNone(engine.detect_category(engine._norm("bugun ob-havo qanday")))

    def test_fuzzy_typo_pharmacy(self):
        # Xato yozilgan so'zlarni ham tushunishi kerak
        self.assertEqual(engine.detect_category(engine._norm("dorxona")), 'pharmacy')
        self.assertEqual(engine.detect_category(engine._norm("aptaka")), 'pharmacy')

    def test_fuzzy_typo_hospital(self):
        self.assertEqual(engine.detect_category(engine._norm("shifoxna")), 'hospital')

    def test_fuzzy_does_not_overmatch(self):
        # "salom" hech qanday toifaga tushmasligi kerak (salomlashish bo'lib qolsin)
        self.assertIsNone(engine.detect_category(engine._norm("salom")))


class IntentTests(TestCase):
    @skipUnless(settings.TAXI_ENABLED, "taksi arxivlangan (TAXI_ENABLED=False)")
    def test_taxi_call_retreats_to_agent(self):
        # «taksi kerak» — CHAQIRISH amali → engine chekinadi (agent taxi hal qiladi)
        self.assertEqual(engine.handle("menga taksi kerak")['intent'], 'unknown')

    def test_taxi_search_stays_engine(self):
        # «taksi qayerda» — qidiruv (harakatsiz) → engine (o'zgarmaydi)
        res = engine.handle("taksi bo'limi qayerda")
        self.assertNotEqual(res['intent'], 'unknown')

    @skipUnless(not settings.TAXI_ENABLED, "taksi yoqilgan")
    def test_taxi_requests_report_disabled(self):
        # Taksi arxivlangan — har qanday taksi so'rovi xizmat yopiqligini aytadi
        # va agentga uzatilmaydi (agentda ham taxi tool yo'q).
        for q in ("menga taksi kerak", "taksi chaqir", "taksistlarni ko'rsat"):
            res = engine.handle(q)
            self.assertEqual(res['intent'], 'taxi_disabled', q)
            self.assertNotIn('taxi', ' '.join(
                a.get('url', '') for a in res.get('actions', [])))

    def test_delivery_action_retreats_to_agent(self):
        # «ovqat yetkazib berish» — yetkazib berish AMALI → engine chekinadi
        # (agent delivery hal qiladi). PROMPT_12: ACTION_INTENT_WORDS ga delivery
        # iboralari qo'shildi, shu bois endi 'delivery' emas, 'unknown' qaytadi.
        self.assertEqual(engine.handle("ovqat yetkazib berish")['intent'], 'unknown')

    def test_delivery_howto_stays_engine(self):
        # «yetkazib berish qanday ishlaydi» — HOW-TO → engine/KB (agentga ketmaydi)
        self.assertNotEqual(engine.is_action_intent("yetkazib berish qanday ishlaydi"), True)

    def test_ads_intent(self):
        res = engine.handle("mashina sotib olaman")
        self.assertEqual(res['intent'], 'ads')

    def test_greeting(self):
        self.assertEqual(engine.handle("salom")['intent'], 'greeting')

    def test_help(self):
        self.assertEqual(engine.handle("nima qila olasan")['intent'], 'help')

    def test_unknown_goes_unknown(self):
        # Mahalliy dvigatel tushunmasa 'unknown' — LLM fallback shu belgidan foydalanadi
        self.assertEqual(engine.handle("kvant fizikasi haqida gapir")['intent'], 'unknown')

    def test_empty(self):
        self.assertEqual(engine.handle("")['intent'], 'empty')

    def test_categories_match_place_model(self):
        # engine dagi toifalar Place modelidagilar bilan mos bo'lishi SHART
        from places.models import CATEGORY_CHOICES
        valid = {c for c, _ in CATEGORY_CHOICES}
        for cat in engine.VALID_CATEGORIES:
            self.assertIn(cat, valid, f"'{cat}' Place.CATEGORY_CHOICES da yo'q")


class NearestPlaceTests(TestCase):
    def setUp(self):
        from places.models import Place
        # Markazga yaqin va uzoq ikkita dorixona
        self.near = Place.objects.create(
            name="Yaqin dorixona", category='pharmacy',
            latitude=engine.CENTER[0] + 0.001, longitude=engine.CENTER[1] + 0.001,
        )
        self.far = Place.objects.create(
            name="Uzoq dorixona", category='pharmacy',
            latitude=engine.CENTER[0] + 0.2, longitude=engine.CENTER[1] + 0.2,
        )

    def test_nearest_uses_center_without_location(self):
        res = engine.handle("eng yaqin dorixona")
        self.assertEqual(res['intent'], 'nearest_place')
        self.assertTrue(res['used_center'])
        self.assertTrue(res['cards'])
        # Birinchi karta — eng yaqin
        self.assertEqual(res['cards'][0]['title'], "Yaqin dorixona")

    def test_nearest_with_location(self):
        # far ga yaqin joydan so'rasak — far birinchi bo'ladi
        loc = (engine.CENTER[0] + 0.21, engine.CENTER[1] + 0.21)
        res = engine.handle("dorixona", location=loc)
        self.assertFalse(res['used_center'])
        self.assertEqual(res['cards'][0]['title'], "Uzoq dorixona")

    def test_card_has_route_and_walk(self):
        res = engine.handle("eng yaqin dorixona")
        card = res['cards'][0]
        self.assertIn('route_url', card)
        self.assertIn('google.com/maps', card['route_url'])
        self.assertIn('walk', card)
        self.assertIn('distance', card)


class ContinuationTests(TestCase):
    def setUp(self):
        from places.models import Place
        # 6 ta dorixona — "yana" offsetni tekshirish uchun
        for i in range(6):
            Place.objects.create(
                name=f"Dorixona {i}", category='pharmacy',
                latitude=engine.CENTER[0] + 0.001 * (i + 1),
                longitude=engine.CENTER[1] + 0.001 * (i + 1),
            )

    def test_first_batch_returns_four(self):
        res = engine.handle("eng yaqin dorixona")
        self.assertEqual(len(res['cards']), 4)
        self.assertEqual(res['category'], 'pharmacy')
        self.assertEqual(res['next_offset'], 4)

    def test_continue_uses_context_offset(self):
        res = engine.handle("yana", context={'last_category': 'pharmacy', 'offset': 4})
        self.assertEqual(res['intent'], 'nearest_place')
        self.assertEqual(res['category'], 'pharmacy')
        # 6 tadan 4 tasi ko'rsatilgan → qolgan 2 tasi
        self.assertEqual(len(res['cards']), 2)

    def test_continue_without_context_is_unknown(self):
        # Kontekstsiz "yana" — toifa yo'q, tushunilmaydi
        res = engine.handle("yana")
        self.assertEqual(res['intent'], 'unknown')


class OpenNowTests(TestCase):
    def test_open_range(self):
        # Kun bo'yi ochiq (00:00–23:59) — hozir albatta ochiq
        self.assertTrue(engine._is_open_now("00:00-23:59"))

    def test_24_hours(self):
        self.assertTrue(engine._is_open_now("24 soat"))

    def test_unparseable(self):
        self.assertIsNone(engine._is_open_now("har kuni"))
        self.assertIsNone(engine._is_open_now(""))


class KnowledgeBaseTests(TestCase):
    """Sayt funksiyalari bo'yicha qo'llanma (FAQ) to'g'ri ishlashini tekshiradi."""

    def _kb_id(self, text):
        e = knowledge.answer(engine._norm(text))
        return e['id'] if e else None

    def test_post_ad(self):
        self.assertEqual(self._kb_id("e'lon qanday joylayman"), 'post_ad')

    def test_open_store(self):
        self.assertEqual(self._kb_id("do'kon ochmoqchiman"), 'open_store')

    @skipUnless(getattr(settings, 'PAYMENTS_ENABLED', False),
                "to'lovlar arxivlangan (PAYMENTS_ENABLED=False)")
    def test_payments(self):
        self.assertEqual(self._kb_id("kommunal to'lovni qanday to'layman"), 'payments')

    def test_mahalla_archived_not_answered(self):
        """Mahalla bo'limi arxivlangan — KB uni javob sifatida QAYTARMASLIGI kerak.

        Aks holda yordamchi ishlamaydigan bo'limga havola berardi."""
        self.assertIsNone(self._kb_id("mahalla bo'limi nima"))

    @skipUnless(settings.TAXI_ENABLED, "taksi arxivlangan (TAXI_ENABLED=False)")
    def test_become_taxist(self):
        self.assertEqual(self._kb_id("taksist bo'lish uchun nima qilay"), 'become_taxist')

    @skipUnless(not settings.TAXI_ENABLED, "taksi yoqilgan")
    def test_taxi_kb_hidden_when_archived(self):
        # Taksi arxivlangan — KB taksi javoblarini bermaydi (havolalar yo'q).
        self.assertIsNone(self._kb_id("taksist bo'lish uchun nima qilay"))
        self.assertIsNone(self._kb_id("taksi qanday buyurtma qilaman"))

    def test_book_venue(self):
        self.assertEqual(self._kb_id("to'yxona qanday bron qilaman"), 'book_venue')

    def test_register(self):
        self.assertEqual(self._kb_id("ro'yxatdan o'tish"), 'register')

    def test_no_false_trigger(self):
        # Salomlashish/joy topish KB ni yolg'on ishga tushirmasligi kerak
        self.assertIsNone(self._kb_id("salom"))
        self.assertIsNone(self._kb_id("bugun ob-havo qanday"))

    def test_handle_returns_faq(self):
        res = engine.handle("e'lon qanday joylayman")
        self.assertEqual(res['intent'], 'faq')
        self.assertEqual(res['kb_id'], 'post_ad')
        self.assertTrue(res['actions'])
        self.assertTrue(all('url' in a for a in res['actions']))

    def test_help_overview_has_actions(self):
        res = engine.handle("nima qila olasan")
        self.assertEqual(res['intent'], 'help')
        self.assertTrue(res['actions'])

    def test_all_kb_urls_are_valid(self):
        """Har bir KB havolasidagi URL nomi haqiqatda mavjudligini tekshiradi.

        Bu test URL nomidagi har qanday xatoni (typo) darhol ushlaydi.
        """
        for entry in knowledge.KB:
            # Taksi arxivlangan — /taxi/ yo'llari ulanmagan, bu yozuvlar
            # javob sifatida ham qaytarilmaydi (knowledge.answer chetlab o'tadi).
            if not settings.TAXI_ENABLED and entry['id'] in knowledge.TAXI_KB_IDS:
                continue
            for label, urlname in entry['actions']:
                try:
                    reverse(urlname)
                except NoReverseMatch as exc:
                    self.fail(f"KB '{entry['id']}' — noto'g'ri URL nomi '{urlname}': {exc}")

    def test_overview_action_urls_or_queries(self):
        # overview_actions faqat 'q' (tez savol) ishlatadi — tekshirib qo'yamiz
        for a in knowledge.overview_actions():
            self.assertTrue(a.get('q') or a.get('url'))


class SmallTalkTests(TestCase):
    def test_thanks(self):
        self.assertEqual(engine.handle("rahmat")['intent'], 'smalltalk')
        self.assertEqual(engine.handle("katta rahmat")['intent'], 'smalltalk')

    def test_bye(self):
        self.assertEqual(engine.handle("xayr")['intent'], 'smalltalk')

    def test_yesno(self):
        self.assertEqual(engine.handle("ha")['intent'], 'smalltalk')
        self.assertEqual(engine.handle("ok")['intent'], 'smalltalk')
        # yesno javobida yo'naltiruvchi tugmalar bo'ladi
        self.assertTrue(engine.handle("ha")['actions'])

    def test_smalltalk_not_unknown(self):
        self.assertNotEqual(engine.handle("rahmat")['intent'], 'unknown')


class FallbackTests(TestCase):
    def test_fallback_has_actions(self):
        fb = engine.fallback(engine._norm("asdfgh qwerty zxcvb"))
        self.assertTrue(fb['reply'])
        self.assertTrue(fb['actions'])


class SmartFilterTests(TestCase):
    def setUp(self):
        from places.models import Place
        # 24 soatlik + oddiy + ish vaqti noma'lum dorixonalar (masofasi ortib boradi)
        Place.objects.create(name="24soat Dori", category='pharmacy', working_hours="24/7",
                             latitude=engine.CENTER[0] + 0.001, longitude=engine.CENTER[1] + 0.001)
        for i, nm in enumerate(["Dori A", "Dori B", "Dori C"], start=2):
            Place.objects.create(name=nm, category='pharmacy', working_hours="08:00–22:00",
                                 latitude=engine.CENTER[0] + 0.001 * i,
                                 longitude=engine.CENTER[1] + 0.001 * i)
        Place.objects.create(name="Dori NoHours", category='pharmacy', working_hours="",
                             latitude=engine.CENTER[0] + 0.01, longitude=engine.CENTER[1] + 0.01)

    def test_quantity_digit(self):
        res = engine.handle("2 ta dorixona")
        self.assertEqual(len(res['cards']), 2)

    def test_quantity_word(self):
        res = engine.handle("uchta dorixona")
        self.assertEqual(len(res['cards']), 3)

    def test_24h_filter(self):
        res = engine.handle("24 soat ishlaydigan dorixona")
        titles = [c['title'] for c in res['cards']]
        self.assertEqual(titles, ["24soat Dori"])

    def test_open_now_excludes_unknown_and_includes_24h(self):
        res = engine.handle("hozir ochiq dorixona")
        titles = [c['title'] for c in res['cards']]
        self.assertIn("24soat Dori", titles)          # 24/7 — doim ochiq
        self.assertNotIn("Dori NoHours", titles)      # ish vaqti noma'lum — chiqarilmaydi
        self.assertTrue(all(c['open'] is True for c in res['cards']))


class FollowupTests(TestCase):
    def setUp(self):
        self.cards = [
            {'title': 'Dorixona Shifo', 'subtitle': 'Markaz 1', 'phone': '+998 90 111 22 33',
             'hours': '08:00–22:00', 'url': '/map/1/', 'route_url': 'http://r/1', 'distance': '340 m'},
            {'title': '24/7 Dorixona', 'subtitle': 'Yoshlik 2', 'phone': '+998 90 444 55 66',
             'hours': '24/7', 'url': '/map/2/', 'route_url': 'http://r/2', 'distance': '900 m'},
        ]

    def test_phone_of_first(self):
        res = engine.handle("birinchisining telefoni", context={'last_cards': self.cards})
        self.assertEqual(res['intent'], 'followup')
        self.assertIn('+998 90 111 22 33', res['reply'])

    def test_address(self):
        res = engine.handle("manzili qayerda", context={'last_cards': self.cards})
        self.assertEqual(res['intent'], 'followup')
        self.assertIn('Markaz 1', res['reply'])

    def test_second_item(self):
        res = engine.handle("ikkinchisining telefoni", context={'last_cards': self.cards})
        self.assertIn('+998 90 444 55 66', res['reply'])

    def test_followup_returns_card(self):
        res = engine.handle("birinchisi haqida", context={'last_cards': self.cards})
        self.assertEqual(len(res['cards']), 1)

    def test_no_context_not_followup(self):
        # Kontekstsiz — follow-up ishlamaydi, oddiy tushunilmagan savolga aylanadi
        res = engine.handle("telefon raqami")
        self.assertNotEqual(res['intent'], 'followup')


class SuggestTests(TestCase):
    """«Balki buni nazarda tutdingizmi?» — fuzzy taklif."""

    def test_suggest_close_word(self):
        sug = engine.suggest(engine._norm("aptekaa"))   # "apteka" ga yaqin
        self.assertIsNotNone(sug)
        self.assertTrue(sug.get('q'))

    def test_suggest_gibberish_none(self):
        self.assertIsNone(engine.suggest(engine._norm("zzzqqqwww")))

    def test_fallback_offers_suggestion(self):
        fb = engine.fallback("aptekaa")
        self.assertIn('demoqchimisiz', fb['reply'])
        self.assertTrue(fb['actions'])
        self.assertTrue(fb['actions'][0].get('q'))

    def test_fallback_gibberish_still_helpful(self):
        fb = engine.fallback("zzzqqqwww")
        self.assertNotIn('demoqchimisiz', fb['reply'])
        self.assertTrue(fb['actions'])  # baribir bo'limlar tugmalari bo'ladi


class UnansweredLogTests(TestCase):
    """Javob berilmagan savollarni jurnalga yozish."""

    def setUp(self):
        cache.clear()  # throttling hisoblagichi testlar orasida oqib ketmasin

    def test_record_creates(self):
        record_unanswered("bu qanaqa savol umuman")
        self.assertEqual(UnansweredQuery.objects.count(), 1)

    def test_record_dedupes_and_counts(self):
        record_unanswered("bir xil savol")
        record_unanswered("Bir xil savol")   # katta harf — normalizatsiya birlashtiradi
        self.assertEqual(UnansweredQuery.objects.count(), 1)
        self.assertEqual(UnansweredQuery.objects.first().count, 2)

    def test_record_empty_ignored(self):
        record_unanswered("")
        record_unanswered("   ")
        self.assertEqual(UnansweredQuery.objects.count(), 0)

    def test_endpoint_logs_unknown(self):
        c = Client()
        resp = c.post(reverse('assistant:chat'),
                      data=json.dumps({'message': 'buni hech kim tushunmaydi qwerty'}),
                      content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(UnansweredQuery.objects.count(), 1)

    def test_endpoint_does_not_log_known(self):
        c = Client()
        resp = c.post(reverse('assistant:chat'),
                      data=json.dumps({'message': "e'lon qanday joylayman"}),
                      content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        # Bu KB (faq) bilan javob beriladi — jurnalga tushmasligi kerak
        self.assertEqual(UnansweredQuery.objects.count(), 0)


class PopularPlacesTests(TestCase):
    def setUp(self):
        from places.models import Place
        Place.objects.create(name="Top Joy", category='tourist', views=100,
                             latitude=engine.CENTER[0], longitude=engine.CENTER[1])
        Place.objects.create(name="Mid Joy", category='bank', views=50,
                             latitude=engine.CENTER[0], longitude=engine.CENTER[1])
        Place.objects.create(name="Low Joy", category='pharmacy', views=10,
                             latitude=engine.CENTER[0], longitude=engine.CENTER[1])

    def test_popular_intent_and_order(self):
        res = engine.handle("mashhur joylar")
        self.assertEqual(res['intent'], 'popular')
        titles = [c['title'] for c in res['cards']]
        self.assertEqual(titles, ["Top Joy", "Mid Joy", "Low Joy"])

    def test_popular_alt_phrasing(self):
        self.assertEqual(engine.handle("nima ko'rsam bo'ladi")['intent'], 'popular')


class RealDataSearchTests(TestCase):
    """Asistant e'lon, ish va to'yxonalarni haqiqiy bazadan qidiradi."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        self.u = get_user_model().objects.create_user(phone='998901112233', password='x')

    def test_ads_search_returns_matching(self):
        from main.models import Ad
        Ad.objects.create(user=self.u, category='boshqa', title='Velosiped sotiladi',
                          description='yaxshi holatda', price=500000, status='active')
        res = engine.handle("velosiped sotib olaman")
        self.assertEqual(res['intent'], 'ads')
        self.assertTrue(any('Velosiped' in c['title'] for c in res['cards']))

    def test_ads_no_match_still_has_links(self):
        res = engine.handle("qwertyuiop sotib olaman")
        self.assertEqual(res['intent'], 'ads')
        self.assertEqual(res['cards'], [])
        self.assertTrue(res['actions'])

    def test_jobs_search_returns_matching(self):
        from main.models import JobAd
        JobAd.objects.create(user=self.u, title='Dasturchi kerak', company='IT Firma',
                             description='Python dasturchi', status='active')
        res = engine.handle("dasturchi ish kerak")
        self.assertEqual(res['intent'], 'jobs')
        self.assertTrue(any('Dasturchi' in c['title'] for c in res['cards']))

    def test_booking_action_retreats_to_agent(self):
        """«zal bron qilish» — HARAKAT niyati → engine chekinadi (PROMPT_9).

        Ilgari engine booking branchи venue kartalarини ko'rsatardi va agentни
        soya qilardi. Endi engine 'unknown' qaytaradi → service agentga uzatadi.
        """
        from booking.models import Venue
        Venue.objects.create(owner=self.u, name='Diyor toyxona', is_active=True)
        res = engine.handle("zal bron qilish")
        self.assertEqual(res['intent'], 'unknown')


class MobileApiTests(TestCase):
    """Mobil Flutter ilova uchun REST API endpoint (/api/assistant/chat/)."""

    def setUp(self):
        cache.clear()

    def test_api_chat_ok(self):
        c = Client()
        resp = c.post(reverse('api:assistant-chat'),
                      data=json.dumps({'message': 'eng yaqin dorixona'}),
                      content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        j = resp.json()
        self.assertTrue(j.get('ok'))
        self.assertIn('reply', j)
        self.assertEqual(j.get('intent'), 'nearest_place')

    def test_api_greeting(self):
        c = Client()
        resp = c.post(reverse('api:assistant-chat'),
                      data=json.dumps({'message': 'salom'}),
                      content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get('intent'), 'greeting')

    def test_api_empty_message(self):
        c = Client()
        resp = c.post(reverse('api:assistant-chat'),
                      data=json.dumps({'message': ''}),
                      content_type='application/json')
        self.assertEqual(resp.status_code, 400)


class TtsEndpointTests(TestCase):
    """Bulutli ovoz (TTS) endpointi. Kalit yo'q — 204 qaytadi (widget brauzerga qaytadi)."""

    def setUp(self):
        cache.clear()

    def test_tts_unconfigured_returns_204(self):
        from unittest import mock
        c = Client()
        with mock.patch.dict('os.environ', {'TTS_PROVIDER': ''}):
            resp = c.post(reverse('assistant:tts'),
                          data=json.dumps({'text': 'salom'}),
                          content_type='application/json')
        self.assertEqual(resp.status_code, 204)

    def test_tts_empty_returns_400(self):
        c = Client()
        resp = c.post(reverse('assistant:tts'),
                      data=json.dumps({'text': ''}),
                      content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_synthesize_none_when_unconfigured(self):
        from unittest import mock
        from assistant import tts
        with mock.patch.dict('os.environ', {'TTS_PROVIDER': ''}):
            self.assertIsNone(tts.synthesize('salom'))
            self.assertFalse(tts.is_enabled())

    def test_api_tts_unconfigured_returns_204(self):
        from unittest import mock
        c = Client()
        with mock.patch.dict('os.environ', {'TTS_PROVIDER': ''}):
            resp = c.post(reverse('api:assistant-tts'),
                          data=json.dumps({'text': 'salom'}),
                          content_type='application/json')
        self.assertEqual(resp.status_code, 204)


class ThrottleTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_rate_limit_kicks_in(self):
        c = Client()
        url = reverse('assistant:chat')
        first = c.post(url, data=json.dumps({'message': 'salom'}),
                       content_type='application/json')
        self.assertEqual(first.status_code, 200)
        last = first
        for _ in range(views.RATE_LIMIT + 2):
            last = c.post(url, data=json.dumps({'message': 'salom'}),
                          content_type='application/json')
        self.assertEqual(last.status_code, 429)
