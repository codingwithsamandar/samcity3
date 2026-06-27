"""Qo'shimcha API testlari: health, me (profil), ads ro'yxati."""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from main.models import User


def _user(phone='+998905000001'):
    return User.objects.create_user(phone=phone, password='Test12345!', is_active=True)


class HealthTests(TestCase):
    def test_health_liveness(self):
        resp = APIClient().get(reverse('api:health'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['status'], 'ok')

    def test_ready_checks_db_and_cache(self):
        resp = APIClient().get(reverse('api:ready'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['status'], 'ready')
        self.assertEqual(resp.data['db'], 'ok')
        self.assertEqual(resp.data['cache'], 'ok')


class MeTests(TestCase):
    def setUp(self):
        self.user = _user()
        self.client = APIClient()

    def test_me_requires_auth(self):
        resp = self.client.get(reverse('api:me'))
        self.assertIn(resp.status_code, (401, 403))

    def test_me_returns_profile(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get(reverse('api:me'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['phone'], self.user.phone)


class AdsListTests(TestCase):
    def test_ads_list_public(self):
        # IsAuthenticatedOrReadOnly — anonim o'qiy oladi
        resp = APIClient().get(reverse('api:ad-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('results', resp.data)
