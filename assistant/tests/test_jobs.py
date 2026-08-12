"""jobs bo'limi — ish/rezyume qidirish + joylash."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from .. import confirm, registry
from . import _fixtures


def _mk_user(phone):
    return get_user_model().objects.create_user(phone=phone, password='x', name='T')


class JobSearchTests(TestCase):
    def setUp(self):
        from main.models import JobAd, ResumeAd
        self.user = _mk_user('998918000001')
        JobAd.objects.create(user=self.user, title='Python dasturchi kerak',
                             company='IT Firma', description='Django tajribasi',
                             salary_min=5000000, salary_max=9000000, status='active')
        ResumeAd.objects.create(user=self.user, title='Haydovchi ishini qidiraman',
                                about='10 yil tajriba', status='active')
        self.ctx = _fixtures.user_ctx(self.user, session_key='jobs')

    def test_search_jobs(self):
        # PROMPT_12: card_list + SelectionSet — «u haqida batafsil» yechilsin.
        res = registry.dispatch('jobs', 'search_jobs', {'query': 'dasturchi'}, self.ctx)
        self.assertEqual(res['ui']['type'], 'card_list')
        self.assertTrue(res['ui']['ref'])
        self.assertIn('Python dasturchi kerak', [it['title'] for it in res['ui']['items']])
        self.assertTrue(all(it.get('job_id') for it in res['ui']['items']))

    def test_search_resumes(self):
        res = registry.dispatch('jobs', 'search_resumes', {'query': 'haydovchi'}, self.ctx)
        self.assertEqual(res['ui']['type'], 'card_list')
        self.assertIn('Haydovchi ishini qidiraman',
                      [it['title'] for it in res['ui']['items']])
        self.assertTrue(all(it.get('resume_id') for it in res['ui']['items']))

    def test_search_jobs_none(self):
        res = registry.dispatch('jobs', 'search_jobs', {'query': 'zzzqqq'}, self.ctx)
        self.assertIsNone(res.get('ui'))


class JobPostTests(TestCase):
    def setUp(self):
        self.user = _mk_user('998918000010')
        self.ctx = _fixtures.user_ctx(self.user, session_key='jobpost')

    def test_post_job_flow(self):
        from main.models import JobAd
        res = registry.dispatch('jobs', 'post_job', {
            'title': 'Sotuvchi kerak', 'company': 'Do\'kon',
            'description': 'Do\'konga sotuvchi', 'salary_min': 3000000}, self.ctx)
        self.assertEqual(res['result_status'], 'pending')
        self.assertEqual(res['ui']['type'], 'confirm')
        self.assertEqual(JobAd.objects.count(), 0)
        confirm.execute(res['pending_id'], self.user)
        self.assertEqual(JobAd.objects.filter(user=self.user).count(), 1)
        job = JobAd.objects.get(user=self.user)
        self.assertEqual(job.title, 'Sotuvchi kerak')
        self.assertEqual(job.salary_min, 3000000)

    def test_post_resume_flow(self):
        from main.models import ResumeAd
        res = registry.dispatch('jobs', 'post_resume', {
            'title': 'Buxgalter', 'about': 'Sertifikatli buxgalter'}, self.ctx)
        confirm.execute(res['pending_id'], self.user)
        self.assertEqual(ResumeAd.objects.filter(user=self.user).count(), 1)

    def test_anonymous_cannot_post_job(self):
        res = registry.dispatch('jobs', 'post_job',
                                {'title': 'X', 'company': 'Y', 'description': 'Z'},
                                _fixtures.anon_ctx())
        self.assertEqual(res['result_status'], 'denied')
