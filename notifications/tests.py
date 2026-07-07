"""Notifications testlari — notify(), DeviceToken API, push o'chiq rejimi."""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from main.models import User
from notifications.models import Notification, DeviceToken, notify
from notifications import push


def make_user(phone):
    return User.objects.create_user(phone=phone, password='Test12345!', is_active=True)


class NotifyTests(TestCase):
    def setUp(self):
        self.user = make_user('+998935000001')

    def test_notify_creates_row(self):
        n = notify(self.user, 'Salom', '/x/', 'order')
        self.assertIsNotNone(n)
        self.assertEqual(Notification.objects.filter(recipient=self.user).count(), 1)
        self.assertEqual(n.category, 'order')

    def test_notify_none_recipient(self):
        self.assertIsNone(notify(None, 'Hech kimga'))
        self.assertEqual(Notification.objects.count(), 0)

    def test_push_disabled_without_credentials(self):
        # FIREBASE_CREDENTIALS_FILE yo'q — push jimgina o'chiq, xato bermaydi.
        self.assertFalse(push.send_push(self.user, 'T', 'B'))


class DeviceTokenApiTests(TestCase):
    def setUp(self):
        self.user = make_user('+998935000002')
        self.other = make_user('+998935000003')
        self.client_api = APIClient()
        self.client_api.force_authenticate(self.user)
        self.url = reverse('api:notifications-device')

    def test_register_requires_auth(self):
        resp = APIClient().post(self.url, {'token': 'abc'}, format='json')
        self.assertIn(resp.status_code, (401, 403))

    def test_register_token(self):
        resp = self.client_api.post(self.url, {'token': 'tok-1', 'platform': 'ios'}, format='json')
        self.assertEqual(resp.status_code, 200)
        dt = DeviceToken.objects.get(token='tok-1')
        self.assertEqual(dt.user, self.user)
        self.assertEqual(dt.platform, 'ios')
        self.assertTrue(dt.is_active)

    def test_register_empty_token_rejected(self):
        resp = self.client_api.post(self.url, {'token': ''}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_reregister_moves_token_to_new_user(self):
        # Bitta telefonda akkaunt almashsa token yangi egaga o'tadi.
        self.client_api.post(self.url, {'token': 'tok-2'}, format='json')
        c2 = APIClient()
        c2.force_authenticate(self.other)
        resp = c2.post(self.url, {'token': 'tok-2'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(DeviceToken.objects.get(token='tok-2').user, self.other)
        self.assertEqual(DeviceToken.objects.filter(token='tok-2').count(), 1)

    def test_unregister_deactivates(self):
        self.client_api.post(self.url, {'token': 'tok-3'}, format='json')
        resp = self.client_api.delete(self.url, {'token': 'tok-3'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(DeviceToken.objects.get(token='tok-3').is_active)

    def test_unregister_only_own_token(self):
        self.client_api.post(self.url, {'token': 'tok-4'}, format='json')
        c2 = APIClient()
        c2.force_authenticate(self.other)
        c2.delete(self.url, {'token': 'tok-4'}, format='json')
        # Boshqa foydalanuvchi o'chira olmaydi — token faol qoladi.
        self.assertTrue(DeviceToken.objects.get(token='tok-4').is_active)
