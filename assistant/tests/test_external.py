"""Tashqi e'lon qidiruvi — OLX parseri (tarmoqsiz) + ads.search integratsiyasi.

Tarmoqqa CHIQMAYDI: OLX javobi namunaviy lug'at bilan, ads.search esa mock
qilingan `external.search` bilan sinaladi (deterministik).
"""

from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from .. import registry
from ..external.base import ExternalListing
from ..external.olx import OlxProvider
from ..external.uybor import UyborProvider
from ..external.avtoelon import AvtoelonProvider
from ..external.hh import HHProvider
from . import _fixtures

# OLX API'sидан bitta obyekt namunasi (qisqartirilgan).
_SAMPLE = {
    'title': 'Velosiped sotiladi',
    'url': 'https://www.olx.uz/d/obyavlenie/velosiped-ID.html',
    'params': [{'key': 'price', 'value': {'label': '1 500 000 сум'}}],
    'location': {'city': {'name': 'Тошкент'}, 'region': {'name': 'Тошкент вилояти'}},
    'photos': [{'link': 'https://cdn/image;s={width}x{height}'}],
}


class OlxParseTests(TestCase):
    def test_parse_basic(self):
        listing = OlxProvider._parse(_SAMPLE)
        self.assertIsNotNone(listing)
        self.assertEqual(listing.source, 'OLX')
        self.assertEqual(listing.title, 'Velosiped sotiladi')
        self.assertIn("so'm", listing.price_label)          # сум → so'm
        self.assertEqual(listing.location, 'Тошкент')
        self.assertIn('320', listing.image)                 # {width} → 320

    def test_parse_arranged_price(self):
        item = dict(_SAMPLE, params=[{'key': 'price',
                                      'value': {'label': '', 'arranged': True}}])
        self.assertEqual(OlxProvider._parse(item).price_label, 'Kelishiladi')

    def test_parse_missing_url_is_none(self):
        self.assertIsNone(OlxProvider._parse({'title': 'x'}))

    def test_to_card_shape(self):
        card = OlxProvider._parse(_SAMPLE).to_card()
        self.assertEqual(card['tags'], ['OLX'])
        self.assertTrue(card['url'])
        self.assertIn("so'm", card['subtitle'])
        self.assertEqual(card['icon'], '🌐')


class UyborParseTests(TestCase):
    SAMPLE = {
        'id': 1318169, 'operationType': 'rent', 'description': 'Chilonzor 1\n1-xona',
        'price': 500, 'priceCurrency': 'usd', 'address': '1-kvartal',
        'room': '1', 'square': 30, 'floor': 2, 'floorTotal': 4,
        'media': [{'url': 'https://api.uybor.uz/api/v1/media/n/x.jpeg'}],
    }

    def test_parse(self):
        l = UyborProvider._parse(self.SAMPLE)
        self.assertIsNotNone(l)
        self.assertEqual(l.source, 'Uybor')
        self.assertIn('Ijara', l.title)
        self.assertIn('1-xona', l.title)
        self.assertIn('u.e.', l.price_label)
        self.assertIn('/oy', l.price_label)
        self.assertTrue(l.url.endswith('/1318169'))

    def test_applies_only_realestate(self):
        p = UyborProvider()
        self.assertTrue(p.applies('kvartira kerak', None))
        self.assertTrue(p.applies('x', 'uy_joy'))
        self.assertFalse(p.applies('velosiped', None))


class AvtoelonParseTests(TestCase):
    HTML = ('<div><a href="/uz/a/show/7375551">Chevrolet Cobalt 2024</a>'
            '<span>~12 500 у.е.</span>'
            '<img src="https://cdn.example/1-200x150.webp"></div>')

    def test_parse(self):
        items = AvtoelonProvider._parse(self.HTML, limit=5)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source, 'Avtoelon')
        self.assertIn('Cobalt', items[0].title)
        self.assertIn('u.e.', items[0].price_label)
        self.assertTrue(items[0].url.endswith('/uz/a/show/7375551'))

    def test_applies_only_cars(self):
        p = AvtoelonProvider()
        self.assertTrue(p.applies('nexia sotaman', None))
        self.assertTrue(p.applies('x', 'avtomobil'))
        self.assertFalse(p.applies('kvartira', None))


class HHParseTests(TestCase):
    SAMPLE = {
        'name': 'Python dasturchi', 'alternate_url': 'https://hh.uz/vacancy/123',
        'employer': {'name': 'Epam'}, 'area': {'name': 'Toshkent'},
        'salary': {'from': 8000000, 'to': 15000000, 'currency': 'UZS'},
    }

    def test_parse(self):
        v = HHProvider._parse(self.SAMPLE)
        self.assertIsNotNone(v)
        self.assertEqual(v.source, 'HH.uz')
        self.assertEqual(v.icon, '💼')
        self.assertIn('Epam', v.location)
        self.assertIn('Toshkent', v.location)
        self.assertIn("so'm", v.price_label)
        self.assertTrue(v.url.endswith('/vacancy/123'))

    def test_parse_no_salary(self):
        item = dict(self.SAMPLE, salary=None)
        self.assertEqual(HHProvider._parse(item).price_label, '')

    def test_domain_is_jobs(self):
        self.assertEqual(HHProvider.domain, 'jobs')


@override_settings(ASSISTANT_EXTERNAL_SEARCH_ENABLED=True)
class JobsExternalIntegrationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            phone='998917000060', password='x', name='T')
        self.ctx = _fixtures.user_ctx(self.user, session_key='jobsext')

    def test_external_jobs_used_when_no_local(self):
        fake = [ExternalListing(title='Python dev', url='https://hh.uz/vacancy/1',
                                source='HH.uz', price_label="8 000 000 so'm",
                                location='Epam', icon='💼')]
        with mock.patch('assistant.external.search', return_value=fake) as m:
            res = registry.dispatch('jobs', 'search_jobs',
                                    {'query': 'dasturchi'}, self.ctx)
        m.assert_called_once()
        self.assertEqual(m.call_args.kwargs.get('domain'), 'jobs')
        self.assertEqual(res['ui']['type'], 'link_list')
        self.assertIn('Python dev', [it['title'] for it in res['ui']['items']])


@override_settings(ASSISTANT_EXTERNAL_SEARCH_ENABLED=True)
class AdsExternalIntegrationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            phone='998917000050', password='x', name='T')
        self.ctx = _fixtures.user_ctx(self.user, session_key='adsext')

    def test_external_used_when_no_local(self):
        fake = [ExternalListing(title='OLX velo', url='https://olx.uz/x',
                                source='OLX', price_label="1 000 000 so'm")]
        with mock.patch('assistant.external.search', return_value=fake) as m:
            res = registry.dispatch('ads', 'search', {'query': 'velosiped'}, self.ctx)
        m.assert_called_once()
        self.assertEqual(res['ui']['type'], 'link_list')
        self.assertIn('OLX velo', [it['title'] for it in res['ui']['items']])

    def test_local_and_external_mixed(self):
        from main.models import Ad
        Ad.objects.create(user=self.user, category='boshqa', title='Bizning velo',
                          price=500000, status='active')
        fake = [ExternalListing(title='OLX velo', url='https://olx.uz/x', source='OLX')]
        with mock.patch('assistant.external.search', return_value=fake):
            res = registry.dispatch('ads', 'search',
                                    {'query': 'velo', 'external': True}, self.ctx)
        titles = [it['title'] for it in res['ui']['items']]
        self.assertEqual(res['ui']['type'], 'link_list')
        self.assertIn('Bizning velo', titles)               # sayt e'loni
        self.assertIn('OLX velo', titles)                   # tashqi e'lon

    def test_no_external_falls_back_to_card_list(self):
        # Tashqi natija bo'sh — sayt e'loni TANLANADIGAN card_list'да qoladi.
        from main.models import Ad
        Ad.objects.create(user=self.user, category='boshqa', title='Yolg\'iz velo',
                          price=500000, status='active')
        with mock.patch('assistant.external.search', return_value=[]):
            res = registry.dispatch('ads', 'search', {'query': 'velo'}, self.ctx)
        self.assertEqual(res['ui']['type'], 'card_list')
        self.assertTrue(all(it.get('ad_id') for it in res['ui']['items']))
