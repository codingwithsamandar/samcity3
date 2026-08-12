"""Arxitektor testsiz qo'shган 3 tool + tajriba filtri.

- delivery.clear_cart — savatni butunlay tozalaydi
- jobs.my_resumes / jobs.my_jobs — foydalanuvchining o'z e'lonlari
- jobs.search_resumes experience filtri (>=)
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from .. import registry
from . import _fixtures


def _mk_user(phone):
    return get_user_model().objects.create_user(phone=phone, password='x', name='T')


class ClearCartTests(TestCase):
    def setUp(self):
        from delivery.models import CartItem, Product, Store, get_active_cart
        self.user = _mk_user('998922000001')
        owner = _mk_user('998922000002')
        store = Store.objects.create(owner=owner, name='Anor', store_type='delivery',
                                     is_active=True)
        p1 = Product.objects.create(store=store, name='Lavash', price=35000,
                                    stock=10, is_available=True)
        p2 = Product.objects.create(store=store, name="Ko'k choy", price=5000,
                                    stock=50, is_available=True)
        cart = get_active_cart(self.user)
        CartItem.objects.create(cart=cart, product=p1, quantity=2)
        CartItem.objects.create(cart=cart, product=p2, quantity=1)
        self.ctx = _fixtures.user_ctx(self.user, session_key='clr')

    def test_clear_cart(self):
        from delivery.models import get_active_cart
        res = registry.dispatch('delivery', 'clear_cart', {}, self.ctx)
        self.assertIn('tozalandi', res['speech'].lower())
        self.assertEqual(get_active_cart(self.user).items.count(), 0)

    def test_clear_empty_cart(self):
        from delivery.models import get_active_cart
        get_active_cart(self.user).items.all().delete()
        res = registry.dispatch('delivery', 'clear_cart', {}, self.ctx)
        self.assertIn("bo'sh", res['speech'].lower())

    def test_clear_cart_requires_auth(self):
        res = registry.dispatch('delivery', 'clear_cart', {}, _fixtures.anon_ctx())
        self.assertEqual(res['result_status'], 'denied')


class MyJobsResumesTests(TestCase):
    def setUp(self):
        from main.models import JobAd, ResumeAd
        self.user = _mk_user('998922100001')
        self.other = _mk_user('998922100002')
        ResumeAd.objects.create(user=self.user, title='Haydovchi', about='...',
                                experience='3_5', status='active')
        JobAd.objects.create(user=self.user, title='Sotuvchi kerak', company='Anor',
                             description='...', status='active')
        self.ctx = _fixtures.user_ctx(self.user, session_key='mine')

    def test_my_resumes(self):
        res = registry.dispatch('jobs', 'my_resumes', {}, self.ctx)
        self.assertEqual(res['ui']['type'], 'link_list')
        self.assertEqual(res['ui']['items'][0]['title'], 'Haydovchi')

    def test_my_jobs(self):
        res = registry.dispatch('jobs', 'my_jobs', {}, self.ctx)
        self.assertEqual(res['ui']['type'], 'link_list')
        self.assertEqual(res['ui']['items'][0]['title'], 'Sotuvchi kerak')

    def test_only_own(self):
        """Boshqa foydalanuvchida e'lon yo'q → bo'sh."""
        ctx = _fixtures.user_ctx(self.other, session_key='oth')
        self.assertIsNone(registry.dispatch('jobs', 'my_resumes', {}, ctx).get('ui'))
        self.assertIsNone(registry.dispatch('jobs', 'my_jobs', {}, ctx).get('ui'))

    def test_require_auth(self):
        res = registry.dispatch('jobs', 'my_resumes', {}, _fixtures.anon_ctx())
        self.assertEqual(res['result_status'], 'denied')


class SearchResumesExpTests(TestCase):
    def setUp(self):
        from main.models import ResumeAd
        self.owner = _mk_user('998922200001')
        for title, exp in [('Dasturchi A', 'no_exp'), ('Dasturchi B', '1_3'),
                           ('Dasturchi C', '5_plus')]:
            ResumeAd.objects.create(user=self.owner, title=title, about='dasturchi',
                                    skills='python', experience=exp, status='active')
        self.ctx = _fixtures.user_ctx(_mk_user('998922200002'), session_key='sr')

    def _titles(self, res):
        return {i['title'] for i in res['ui']['items']}

    def test_no_filter_returns_all(self):
        res = registry.dispatch('jobs', 'search_resumes', {'query': 'dasturchi'}, self.ctx)
        self.assertEqual(len(res['ui']['items']), 3)

    def test_exp_filter_ge(self):
        """3_5 so'ralса → 3_5 va 5_plus (>=). Bu yerда faqat 5_plus mavjud."""
        res = registry.dispatch('jobs', 'search_resumes',
                                {'query': 'dasturchi', 'experience': '3_5'}, self.ctx)
        self.assertEqual(self._titles(res), {'Dasturchi C'})

    def test_exp_filter_min(self):
        res = registry.dispatch('jobs', 'search_resumes',
                                {'query': 'dasturchi', 'experience': '1_3'}, self.ctx)
        self.assertEqual(self._titles(res), {'Dasturchi B', 'Dasturchi C'})

    def test_natural_language_map(self):
        """«5 yildan ko'p» → 5_plus."""
        res = registry.dispatch('jobs', 'search_resumes',
                                {'query': 'dasturchi', 'experience': "5 yildan ko'p"},
                                self.ctx)
        self.assertEqual(self._titles(res), {'Dasturchi C'})


class MapExperienceTests(TestCase):
    def test_map(self):
        from ..tools.jobs import _map_experience
        self.assertEqual(_map_experience('tajribasiz'), 'no_exp')
        self.assertEqual(_map_experience('katta tajribali'), '5_plus')
        self.assertEqual(_map_experience('3 yillik tajriba'), '1_3')
        self.assertEqual(_map_experience('5_plus'), '5_plus')
        self.assertIsNone(_map_experience(''))
        self.assertIsNone(_map_experience(None))
