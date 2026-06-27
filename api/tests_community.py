"""Community (so'rovnoma/yordam), jobs, service API testlari + permission."""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from main.models import User, Poll, PollOption, PollVote, HelpRequest, JobAd, ResumeAd
from payments.models import Provider


def make_user(phone):
    return User.objects.create_user(phone=phone, password='Test12345!', is_active=True)


# ─────────────────────── So'rovnomalar ───────────────────────
class PollApiTests(TestCase):
    def setUp(self):
        self.user = make_user('+998934000001')
        self.poll = Poll.objects.create(
            creator=self.user, question='Eng yaxshi park?', poll_type='single', is_active=True)
        self.opt_a = PollOption.objects.create(poll=self.poll, text='Markaziy', order=0)
        self.opt_b = PollOption.objects.create(poll=self.poll, text='Yoshlar', order=1)

    def test_poll_list_public(self):
        resp = APIClient().get(reverse('api:polls'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data['results']), 1)

    def test_vote_requires_auth(self):
        resp = APIClient().post(reverse('api:poll-vote', args=[self.poll.id]),
                                {'options': [self.opt_a.id]}, format='json')
        self.assertIn(resp.status_code, (401, 403))

    def test_vote_records_and_updates(self):
        c = APIClient(); c.force_authenticate(self.user)
        r = c.post(reverse('api:poll-vote', args=[self.poll.id]),
                   {'options': [self.opt_a.id]}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(PollVote.objects.filter(option=self.opt_a).count(), 1)
        self.assertIn(self.opt_a.id, r.data['my_votes'])

    def test_single_vote_replaces_previous(self):
        c = APIClient(); c.force_authenticate(self.user)
        c.post(reverse('api:poll-vote', args=[self.poll.id]),
               {'options': [self.opt_a.id]}, format='json')
        c.post(reverse('api:poll-vote', args=[self.poll.id]),
               {'options': [self.opt_b.id]}, format='json')
        # single — faqat bitta ovoz qoladi
        self.assertEqual(PollVote.objects.filter(option__poll=self.poll, user=self.user).count(), 1)
        self.assertEqual(PollVote.objects.filter(option=self.opt_b).count(), 1)


# ─────────────────────── Yordam markazi ───────────────────────
class HelpApiTests(TestCase):
    def setUp(self):
        self.user = make_user('+998934000010')

    def test_list_public(self):
        HelpRequest.objects.create(creator=self.user, title='Yordam', description='...')
        resp = APIClient().get(reverse('api:help'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('categories', resp.data)
        self.assertEqual(len(resp.data['results']), 1)

    def test_create_requires_auth(self):
        resp = APIClient().post(reverse('api:help'),
                                {'title': 'X', 'description': 'Y'}, format='json')
        self.assertIn(resp.status_code, (401, 403))

    def test_create_ok(self):
        c = APIClient(); c.force_authenticate(self.user)
        resp = c.post(reverse('api:help'),
                      {'title': 'Qon kerak', 'description': 'Shoshilinch', 'category': 'blood'},
                      format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(HelpRequest.objects.filter(creator=self.user).count(), 1)

    def test_create_validation(self):
        c = APIClient(); c.force_authenticate(self.user)
        resp = c.post(reverse('api:help'), {'title': ''}, format='json')
        self.assertEqual(resp.status_code, 400)


# ─────────────────────── Ish / Rezyume ───────────────────────
class JobsApiTests(TestCase):
    def setUp(self):
        self.user = make_user('+998934000020')

    def test_jobs_list_public(self):
        resp = APIClient().get(reverse('api:jobs'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('results', resp.data)

    def test_create_job_requires_auth(self):
        resp = APIClient().post(reverse('api:jobs'),
                                {'title': 'Sotuvchi', 'company': 'X', 'description': 'Y'},
                                format='json')
        self.assertIn(resp.status_code, (401, 403))

    def test_create_job_ok(self):
        c = APIClient(); c.force_authenticate(self.user)
        resp = c.post(reverse('api:jobs'),
                      {'title': 'Oshpaz', 'company': 'Restoran', 'description': 'Tajriba kerak'},
                      format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(JobAd.objects.count(), 1)

    def test_create_resume_ok(self):
        c = APIClient(); c.force_authenticate(self.user)
        resp = c.post(reverse('api:resumes'),
                      {'title': 'Dasturchi', 'about': 'Python'}, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(ResumeAd.objects.count(), 1)


# ─────────────────────── Xizmat to'lovlari (provayderlar) ───────────────────────
class ServiceProvidersTests(TestCase):
    def test_providers_list(self):
        Provider.objects.create(name='Elektr tarmoqlari', category='kommunal',
                                amount=0, is_active=True)
        resp = APIClient().get(reverse('api:service-providers'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('categories', resp.data)
        self.assertEqual(len(resp.data['results']), 1)

    def test_create_payment_requires_auth(self):
        p = Provider.objects.create(name='Suv', category='kommunal', amount=50000, is_active=True)
        resp = APIClient().post(reverse('api:service-pay'),
                                {'provider': str(p.id), 'amount': 50000}, format='json')
        self.assertIn(resp.status_code, (401, 403))
