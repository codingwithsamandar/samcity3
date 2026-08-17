"""Admin sahifalari haqiqatan ochiladimi (autocomplete, fieldset, amallar)."""
from django.test import TestCase
from django.urls import reverse

from main.models import User
from delivery.models import DeliveryDriver


class DriverAdminPageTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_superuser(
            phone='+998935000001', password='Test12345!')
        self.client.force_login(self.staff)

    def test_add_page_opens(self):
        resp = self.client.get(reverse('admin:delivery_deliverydriver_add'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'admin-autocomplete')          # qidiruvli tanlov
        self.assertContains(resp, 'Transport')                    # fieldset

    def test_changelist_shows_actions_and_column(self):
        person = User.objects.create_user(phone='+998935000002', password='Test12345!')
        DeliveryDriver.objects.create(user=person, full_name='K', phone='+998935000002', status='approved')
        resp = self.client.get(reverse('admin:delivery_deliverydriver_changelist'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Bloklash')
        self.assertContains(resp, 'Blokdan chiqarish')
        self.assertContains(resp, "lidagi buyurtma")             # yangi ustun

    def test_user_autocomplete_endpoint_finds_by_phone(self):
        User.objects.create_user(phone='+998935000077', password='Test12345!')
        resp = self.client.get(reverse('admin:autocomplete'), {
            'app_label': 'delivery', 'model_name': 'deliverydriver',
            'field_name': 'user', 'term': '935000077',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['results']), 1)
