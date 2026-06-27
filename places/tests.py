"""Places testlari — model, API ro'yxat, egalik ruxsati."""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from main.models import User
from places.models import Place


def make_user(phone):
    return User.objects.create_user(phone=phone, password='Test12345!', is_active=True)


class PlaceModelTests(TestCase):
    def test_create_place(self):
        u = make_user('+998933000001')
        p = Place.objects.create(
            owner=u, name='Dorixona Shifo', category='pharmacy',
            latitude=40.115, longitude=64.503, is_active=True)
        self.assertTrue(p.is_active)
        # icon/color property'lari xato bermasligi kerak
        self.assertTrue(isinstance(p.icon, str))
        self.assertTrue(isinstance(p.color, str))


class PlacesApiTests(TestCase):
    def setUp(self):
        self.owner = make_user('+998933000002')
        Place.objects.create(owner=self.owner, name='Bank', category='bank',
                             latitude=40.11, longitude=64.50, is_active=True)
        Place.objects.create(owner=self.owner, name='Yashirin', category='bank',
                             latitude=40.12, longitude=64.51, is_active=False)

    def test_list_returns_only_active(self):
        resp = APIClient().get(reverse('api:places'))
        self.assertEqual(resp.status_code, 200)
        names = [p['name'] for p in resp.data['results']]
        self.assertIn('Bank', names)
        self.assertNotIn('Yashirin', names)
        self.assertIn('categories', resp.data)

    def test_category_filter(self):
        resp = APIClient().get(reverse('api:places'), {'category': 'bank'})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(all(p['category'] == 'bank' for p in resp.data['results']))


class PlaceOwnerPermissionTests(TestCase):
    def setUp(self):
        self.owner = make_user('+998933000003')
        self.other = make_user('+998933000004')
        self.place = Place.objects.create(
            owner=self.owner, name='Mehmonxona', category='hotel',
            latitude=40.11, longitude=64.50, is_active=True)

    def test_create_requires_login(self):
        resp = self.client.get(reverse('places:place_create'))
        # login_required → login sahifasiga redirect
        self.assertEqual(resp.status_code, 302)

    def test_non_owner_cannot_edit(self):
        self.client.force_login(self.other)
        resp = self.client.post(reverse('places:place_edit', args=[self.place.pk]),
                                {'name': 'Buzildi'})
        self.assertEqual(resp.status_code, 302)  # ruxsat yo'q → redirect
        self.place.refresh_from_db()
        self.assertEqual(self.place.name, 'Mehmonxona')
