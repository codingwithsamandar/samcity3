"""ads bo'limi — e'lon qidirish + joylash (mutating → confirm → Ad)."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from .. import confirm, registry
from ..models import PendingAction
from . import _fixtures


def _mk_user(phone):
    return get_user_model().objects.create_user(phone=phone, password='x', name='T')


class AdsSearchTests(TestCase):
    def setUp(self):
        from main.models import Ad
        self.user = _mk_user('998917000001')
        Ad.objects.create(user=self.user, category='avtomobil', title='Nexia sotiladi',
                          description='yaxshi holatda', price=8000000, status='active',
                          contact_phone='998901112233')
        Ad.objects.create(user=self.user, category='uy_joy', title='Kvartira ijaraga',
                          price=2000000, status='active')
        self.ctx = _fixtures.user_ctx(self.user, session_key='ads')

    def test_search_returns_card_list(self):
        # PROMPT_12: card_list + SelectionSet — «u haqida batafsil» yechilsin.
        res = registry.dispatch('ads', 'search', {'query': 'nexia'}, self.ctx)
        self.assertTrue(res['ok'])
        self.assertEqual(res['ui']['type'], 'card_list')
        self.assertTrue(res['ui']['ref'])
        self.assertIn('Nexia sotiladi', [it['title'] for it in res['ui']['items']])
        self.assertTrue(all(it.get('ad_id') for it in res['ui']['items']))

    def test_search_category_filter(self):
        res = registry.dispatch('ads', 'search',
                                {'query': 'sotiladi ijaraga', 'category': 'uy_joy'}, self.ctx)
        titles = [it['title'] for it in res['ui']['items']]
        self.assertIn('Kvartira ijaraga', titles)
        self.assertNotIn('Nexia sotiladi', titles)

    def test_search_no_match(self):
        res = registry.dispatch('ads', 'search', {'query': 'qwertyuiop'}, self.ctx)
        self.assertIsNone(res.get('ui'))
        self.assertIn('topilmadi', res['speech'].lower())


class AdsPostTests(TestCase):
    def setUp(self):
        self.user = _mk_user('998917000010')
        self.ctx = _fixtures.user_ctx(self.user, session_key='adspost')

    def test_post_creates_pending_not_ad(self):
        from main.models import Ad
        res = registry.dispatch('ads', 'post', {
            'title': 'Velosiped sotiladi', 'category': 'boshqa',
            'price': 500000, 'description': 'deyarli yangi'}, self.ctx)
        self.assertEqual(res['result_status'], 'pending')
        self.assertEqual(res['ui']['type'], 'confirm')
        self.assertEqual(Ad.objects.count(), 0)                # hali yaratilmadi
        self.assertTrue(res['ui'].get('action_url'))           # tugma havolasi to'ldirilgan

    def test_confirm_creates_ad(self):
        from main.models import Ad
        res = registry.dispatch('ads', 'post', {
            'title': 'Velosiped sotiladi', 'category': 'boshqa', 'price': 500000}, self.ctx)
        out = confirm.execute(res['pending_id'], self.user)
        self.assertTrue(out['ok'])
        self.assertEqual(Ad.objects.filter(user=self.user).count(), 1)
        ad = Ad.objects.get(user=self.user)
        self.assertEqual(ad.title, 'Velosiped sotiladi')
        self.assertEqual(ad.price, 500000)
        self.assertEqual(ad.status, 'active')

    def test_free_ad(self):
        from main.models import Ad
        res = registry.dispatch('ads', 'post', {
            'title': 'Kitoblar bepul', 'category': 'boshqa'}, self.ctx)
        confirm.execute(res['pending_id'], self.user)
        ad = Ad.objects.get(user=self.user)
        self.assertEqual(ad.price_type, 'free')

    def test_anonymous_cannot_post(self):
        res = registry.dispatch('ads', 'post',
                                {'title': 'X', 'category': 'boshqa'}, _fixtures.anon_ctx())
        self.assertFalse(res['ok'])
        self.assertEqual(res['result_status'], 'denied')
        self.assertEqual(PendingAction.objects.count(), 0)

    def test_double_confirm_one_ad(self):
        from main.models import Ad
        res = registry.dispatch('ads', 'post',
                                {'title': 'Stol', 'category': 'boshqa'}, self.ctx)
        confirm.execute(res['pending_id'], self.user)
        confirm.execute(res['pending_id'], self.user)
        self.assertEqual(Ad.objects.filter(user=self.user).count(), 1)
