"""selection.py testlari — ovoz bilan tanlashni LLM'siz yechish."""

from django.test import TestCase
from django.utils import timezone

from .. import selection
from ..models import SelectionSet


ITEMS = [
    {'id': 'store:1', 'index': 1, 'title': 'Anor Fast Food',
     'aliases': ['anor', 'anor fast food'], 'price': 35000, 'distance': 1.2, 'rating': 4.8},
    {'id': 'store:2', 'index': 2, 'title': 'Behzod Lavash',
     'aliases': ['behzod', 'behzod lavash'], 'price': 28000, 'distance': 0.6, 'rating': 4.5},
    {'id': 'store:3', 'index': 3, 'title': 'Shirin Choyxona',
     'aliases': ['shirin', 'shirin choyxona'], 'price': 52000, 'distance': 2.4, 'rating': 4.9},
]


class OrdinalTests(TestCase):
    def test_first(self):
        self.assertEqual(selection.resolve_items(ITEMS, "birinchisini")['id'], 'store:1')

    def test_second_numeric(self):
        self.assertEqual(selection.resolve_items(ITEMS, "2-chi")['id'], 'store:2')

    def test_second_word(self):
        self.assertEqual(selection.resolve_items(ITEMS, "ikkinchisini tanladim")['id'],
                         'store:2')

    def test_last(self):
        self.assertEqual(selection.resolve_items(ITEMS, "oxirgisini")['id'], 'store:3')

    def test_out_of_range_ordinal_is_none(self):
        # 9-chi yo'q — tartib bo'yicha topilmaydi (keyingi bosqichlar ham topa olmaydi)
        self.assertIsNone(selection.resolve_items(ITEMS, "9-chi"))


class NameTests(TestCase):
    def test_direct_alias(self):
        self.assertEqual(selection.resolve_items(ITEMS, "anorni")['id'], 'store:1')

    def test_full_title_word(self):
        self.assertEqual(selection.resolve_items(ITEMS, "behzod lavashni ber")['id'],
                         'store:2')


class FuzzyTests(TestCase):
    def test_typo_anur(self):
        self.assertEqual(selection.resolve_items(ITEMS, "anur")['id'], 'store:1')

    def test_typo_behzot(self):
        self.assertEqual(selection.resolve_items(ITEMS, "behzot")['id'], 'store:2')

    def test_gibberish_none(self):
        self.assertIsNone(selection.resolve_items(ITEMS, "qwxyz zzz"))


class SuperlativeTests(TestCase):
    def test_cheapest(self):
        self.assertEqual(selection.resolve_items(ITEMS, "eng arzonini")['id'], 'store:2')

    def test_most_expensive(self):
        self.assertEqual(selection.resolve_items(ITEMS, "eng qimmatini")['id'], 'store:3')

    def test_nearest(self):
        self.assertEqual(selection.resolve_items(ITEMS, "eng yaqinini")['id'], 'store:2')

    def test_best_rated(self):
        self.assertEqual(selection.resolve_items(ITEMS, "eng yaxshi reytinglisini")['id'],
                         'store:3')


class DbLoadTests(TestCase):
    def test_resolve_from_db(self):
        ss = SelectionSet.objects.create(section='delivery', items=ITEMS)
        self.assertEqual(selection.resolve(ss.ref, "anorni")['id'], 'store:1')

    def test_expired_selection_returns_none(self):
        ss = SelectionSet.objects.create(section='delivery', items=ITEMS)
        SelectionSet.objects.filter(ref=ss.ref).update(
            expires_at=timezone.now() - timezone.timedelta(minutes=1))
        self.assertIsNone(selection.resolve(ss.ref, "anorni"))

    def test_unknown_ref_none(self):
        self.assertIsNone(selection.resolve('nonexistent', "anorni"))
