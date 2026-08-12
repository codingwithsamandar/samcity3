"""ads.list_my + cancel oqimi — «bekor qil» chalkаshligiga aniq javob."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from .. import confirm, registry
from . import _fixtures


def _mk_user(phone):
    return get_user_model().objects.create_user(phone=phone, password='x', name='T')


class AdsCancelTests(TestCase):
    def setUp(self):
        from main.models import Ad
        self.user = _mk_user('998924000001')
        self.other = _mk_user('998924000002')
        self.ad = Ad.objects.create(user=self.user, category='avtomobil',
                                    title='Nexia 2015', price=8000000, status='active')
        self.ctx = _fixtures.user_ctx(self.user, session_key='adc')

    def test_list_my(self):
        res = registry.dispatch('ads', 'list_my', {}, self.ctx)
        self.assertEqual(res['ui']['items'][0]['title'], 'Nexia 2015')

    def test_list_my_empty(self):
        ctx = _fixtures.user_ctx(self.other, session_key='o')
        self.assertIsNone(registry.dispatch('ads', 'list_my', {}, ctx).get('ui'))

    def test_cancel_flow(self):
        from main.models import Ad
        res = registry.dispatch('ads', 'cancel', {'ad_id': str(self.ad.pk)}, self.ctx)
        self.assertEqual(res['result_status'], 'pending')
        confirm.execute(res['pending_id'], self.user)
        self.ad.refresh_from_db()
        self.assertEqual(self.ad.status, 'deleted')

    def test_cannot_cancel_others_ad(self):
        ctx = _fixtures.user_ctx(self.other, session_key='o2')
        res = registry.dispatch('ads', 'cancel', {'ad_id': str(self.ad.pk)}, ctx)
        self.assertEqual(res['result_status'], 'denied')

    def test_cancel_prefixed_id(self):
        res = registry.dispatch('ads', 'cancel', {'ad_id': f'ad:{self.ad.pk}'}, self.ctx)
        self.assertEqual(res['result_status'], 'pending')

    def test_cancel_requires_auth(self):
        res = registry.dispatch('ads', 'cancel', {'ad_id': str(self.ad.pk)},
                                _fixtures.anon_ctx())
        self.assertEqual(res['result_status'], 'denied')
