"""Joy qidiruvi testlari — transliteratsiya, manzil, xatoga chidamlilik.

    python manage.py test places.test_search
"""
import json

from django.test import TestCase
from django.urls import reverse

from places.models import Place
from places.search import normalize, score


class NormalizeTests(TestCase):
    def test_cyrillic_and_latin_match(self):
        self.assertEqual(normalize('Навоий'), normalize('Navoiy'))
        self.assertEqual(normalize('Шофиркон'), normalize('Shofirkon'))
        self.assertEqual(normalize('Бухоро'), normalize('Buxoro'))

    def test_apostrophe_variants_match(self):
        base = normalize("Ko'cha")
        self.assertEqual(base, normalize('Koʻcha'))
        self.assertEqual(base, normalize('Ko‘cha'))
        self.assertEqual(base, normalize('Kocha'))

    def test_punctuation_and_case_ignored(self):
        self.assertEqual(normalize('  RESTORAN,  "Anor"! '), normalize('restoran anor'))

    def test_h_and_x_unified(self):
        self.assertEqual(normalize('Xolboyev'), normalize('Holboyev'))

    def test_empty_input(self):
        self.assertEqual(normalize(''), '')
        self.assertEqual(normalize(None), '')


class ScoreTests(TestCase):
    def test_prefix_beats_substring(self):
        self.assertGreater(score('anor', 'Anor Restoran'), score('anor', 'Katta Anor'))

    def test_typo_tolerated(self):
        self.assertGreater(score('restaran', 'Restoran'), 0)
        self.assertGreater(score('dorixona', 'Dorixona'), 0)

    def test_short_query_does_not_fuzzy_match_everything(self):
        """2-3 harfli so'rov xato-chidamlilikka kirmaydi (bazani qaytarmasin)."""
        self.assertEqual(score('xy', 'Anor Restoran'), 0)

    def test_no_match_returns_zero(self):
        self.assertEqual(score('qwertyuiop', 'Anor Restoran'), 0)

    def test_empty_query_returns_zero(self):
        self.assertEqual(score('', 'Anor Restoran'), 0)


class SearchApiTests(TestCase):
    def setUp(self):
        self.anor = Place.objects.create(
            name='Anor Restoran', category='restaurant',
            latitude=40.115, longitude=64.503, address="Navoiy ko'chasi 12")
        self.shifo = Place.objects.create(
            name='Shifo dorixona', name_ru='Аптека Шифо', category='pharmacy',
            latitude=40.116, longitude=64.504, address='Markaziy maydon')
        self.yopiq = Place.objects.create(
            name='Yopiq joy', category='restaurant',
            latitude=40.117, longitude=64.505, is_active=False)

    def _q(self, q, **extra):
        params = {'q': q}
        params.update(extra)
        resp = self.client.get(reverse('places:search_api'), params)
        return [r['name'] for r in json.loads(resp.content)['results']]

    def test_search_by_name(self):
        self.assertIn('Anor Restoran', self._q('anor'))

    def test_search_by_address(self):
        """Ilgari manzil bo'yicha qidirib bo'lmasdi."""
        self.assertIn('Anor Restoran', self._q('navoiy'))

    def test_search_by_cyrillic(self):
        """Kirillcha yozilgan so'rov lotincha nomni topadi."""
        self.assertIn('Anor Restoran', self._q('Анор'))

    def test_search_by_category_label(self):
        self.assertIn('Shifo dorixona', self._q('dorixona'))

    def test_typo_still_finds(self):
        self.assertIn('Anor Restoran', self._q('restaran'))

    def test_inactive_place_excluded(self):
        self.assertNotIn('Yopiq joy', self._q('yopiq'))

    def test_category_filter_applied(self):
        names = self._q('a', category='pharmacy')
        self.assertNotIn('Anor Restoran', names)

    def test_empty_query_returns_nothing(self):
        self.assertEqual(self._q(''), [])

    def test_results_have_map_fields(self):
        resp = self.client.get(reverse('places:search_api'), {'q': 'anor'})
        row = json.loads(resp.content)['results'][0]
        for key in ('id', 'name', 'lat', 'lng', 'icon', 'color', 'url', 'category'):
            self.assertIn(key, row)

    def test_best_match_comes_first(self):
        Place.objects.create(name='Boshqa joy — anor bog\'i', category='tourist',
                             latitude=40.12, longitude=64.51)
        self.assertEqual(self._q('anor restoran')[0], 'Anor Restoran')


class NearbySearchTranslitTests(TestCase):
    """«Yaqinimda» ham xuddi shu qoidada ishlashi kerak."""

    def setUp(self):
        Place.objects.create(name='Anor Restoran', category='restaurant',
                             latitude=40.1156, longitude=64.5036)

    def test_cyrillic_query_works_on_nearby(self):
        resp = self.client.get(reverse('places:nearby'),
                               {'lat': 40.1156, 'lng': 64.5036, 'q': 'Анор'})
        self.assertContains(resp, 'Anor Restoran')

    def test_typo_works_on_nearby(self):
        resp = self.client.get(reverse('places:nearby'),
                               {'lat': 40.1156, 'lng': 64.5036, 'q': 'restaran'})
        self.assertContains(resp, 'Anor Restoran')
