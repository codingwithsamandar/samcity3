"""«U haqida batafsil» — ads.details / jobs.job_details / jobs.resume_details.

Qidiruv card_list + SelectionSet qaytaradi; tanlov `selection.resolve_items`
bilan yechiladi va details tool'i to'liq ma'lumot beradi.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from .. import registry, selection as sel
from . import _fixtures


def _mk_user(phone):
    return get_user_model().objects.create_user(phone=phone, password='x', name='T')


class AdDetailsTests(TestCase):
    def setUp(self):
        from main.models import Ad
        self.user = _mk_user('998925000001')
        self.ad = Ad.objects.create(user=self.user, category='avtomobil',
                                    title='Nexia sotiladi', price=8000000,
                                    description='Yaxshi holatda', location='Shofirkon',
                                    contact_phone='998901112233', status='active')
        self.ctx = _fixtures.user_ctx(self.user, session_key='det')

    def test_details(self):
        res = registry.dispatch('ads', 'details', {'ad_id': str(self.ad.pk)}, self.ctx)
        self.assertEqual(res['ui']['title'], 'Nexia sotiladi')
        self.assertIn('Yaxshi holatda', res['ui']['note'])

    def test_details_prefixed(self):
        res = registry.dispatch('ads', 'details', {'ad_id': f'ad:{self.ad.pk}'}, self.ctx)
        self.assertEqual(res['ui']['title'], 'Nexia sotiladi')

    def test_details_missing(self):
        res = registry.dispatch('ads', 'details', {'ad_id': 'yoq'}, self.ctx)
        self.assertFalse(res['ok'])

    def test_search_then_resolve_first(self):
        """«birinchisi» → selection orqali ad_id topiladi → details ishlaydi."""
        res = registry.dispatch('ads', 'search', {'query': 'nexia'}, self.ctx)
        items = res['ui']['items']
        picked = sel.resolve_items(items, 'birinchisi haqida batafsil')
        self.assertIsNotNone(picked)
        det = registry.dispatch('ads', 'details', {'ad_id': picked['ad_id']}, self.ctx)
        self.assertEqual(det['ui']['title'], 'Nexia sotiladi')


class JobResumeDetailsTests(TestCase):
    def setUp(self):
        from main.models import JobAd, ResumeAd
        self.user = _mk_user('998925100001')
        self.job = JobAd.objects.create(user=self.user, title='Python dasturchi kerak',
                                        company='SamCity', description='Backend ish',
                                        salary_min=5000000, salary_max=9000000,
                                        status='active')
        self.resume = ResumeAd.objects.create(user=self.user, title='Haydovchi',
                                              about='10 yil tajriba', skills='B toifa',
                                              experience='5_plus', status='active')
        self.ctx = _fixtures.user_ctx(self.user, session_key='jd')

    def test_job_details(self):
        res = registry.dispatch('jobs', 'job_details', {'job_id': str(self.job.pk)},
                                self.ctx)
        self.assertEqual(res['ui']['title'], 'Python dasturchi kerak')
        self.assertIn('Backend ish', res['ui']['note'])

    def test_resume_details(self):
        res = registry.dispatch('jobs', 'resume_details',
                                {'resume_id': str(self.resume.pk)}, self.ctx)
        self.assertEqual(res['ui']['title'], 'Haydovchi')
        self.assertIn('10 yil tajriba', res['ui']['note'])

    def test_job_details_missing(self):
        res = registry.dispatch('jobs', 'job_details', {'job_id': 'yoq'}, self.ctx)
        self.assertFalse(res['ok'])

    def test_search_then_details(self):
        res = registry.dispatch('jobs', 'search_jobs', {'query': 'dasturchi'}, self.ctx)
        picked = sel.resolve_items(res['ui']['items'], 'birinchisi haqida batafsil')
        self.assertIsNotNone(picked)
        det = registry.dispatch('jobs', 'job_details', {'job_id': picked['job_id']},
                                self.ctx)
        self.assertEqual(det['ui']['title'], 'Python dasturchi kerak')


class IdentifierTests(TestCase):
    def test_identifier_of_new_keys(self):
        self.assertEqual(sel.identifier_of({'ad_id': 'a1'}), 'ad_id=a1')
        self.assertEqual(sel.identifier_of({'job_id': 'j1'}), 'job_id=j1')
        self.assertEqual(sel.identifier_of({'resume_id': 'r1'}), 'resume_id=r1')
