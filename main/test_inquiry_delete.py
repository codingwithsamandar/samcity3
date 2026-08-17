"""E'lon savollarini o'chirish testlari.

    python manage.py test main.test_inquiry_delete
"""
from django.test import TestCase
from django.urls import reverse

from main.models import User, Ad, AdInquiry


class InquiryDeleteTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(phone='+998910000401', password='x', is_active=True)
        self.buyer = User.objects.create_user(phone='+998910000402', password='x', is_active=True)
        self.stranger = User.objects.create_user(phone='+998910000403', password='x', is_active=True)
        self.ad = Ad.objects.create(user=self.seller, title='Divan sotiladi', price=1000000)
        self.inq = AdInquiry.objects.create(ad=self.ad, sender=self.buyer, message='Yetkazib berasizmi bugun?')

    def _delete(self, user):
        self.client.force_login(user)
        return self.client.post(reverse('inquiry_delete', args=[self.inq.pk]), follow=True)

    def test_seller_can_delete_received_inquiry(self):
        self._delete(self.seller)
        self.assertFalse(AdInquiry.objects.filter(pk=self.inq.pk).exists())

    def test_sender_can_delete_own_inquiry(self):
        self._delete(self.buyer)
        self.assertFalse(AdInquiry.objects.filter(pk=self.inq.pk).exists())

    def test_stranger_cannot_delete(self):
        resp = self._delete(self.stranger)
        self.assertTrue(AdInquiry.objects.filter(pk=self.inq.pk).exists())
        self.assertContains(resp, "huquqingiz yo&#x27;q")

    def test_anonymous_redirected_to_login(self):
        resp = self.client.post(reverse('inquiry_delete', args=[self.inq.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(AdInquiry.objects.filter(pk=self.inq.pk).exists())

    def test_get_not_allowed(self):
        self.client.force_login(self.seller)
        resp = self.client.get(reverse('inquiry_delete', args=[self.inq.pk]))
        self.assertEqual(resp.status_code, 405)
        self.assertTrue(AdInquiry.objects.filter(pk=self.inq.pk).exists())

    # ── Ko'rinishi ──────────────────────────────────────────────────────────
    def test_seller_sees_delete_button_on_ad_page(self):
        self.client.force_login(self.seller)
        resp = self.client.get(reverse('ad_detail', args=[self.ad.pk]))
        self.assertContains(resp, reverse('inquiry_delete', args=[self.inq.pk]))

    def test_buyer_sees_own_message_and_delete_button(self):
        self.client.force_login(self.buyer)
        resp = self.client.get(reverse('ad_detail', args=[self.ad.pk]))
        self.assertContains(resp, 'Yetkazib berasizmi bugun?')
        self.assertContains(resp, reverse('inquiry_delete', args=[self.inq.pk]))

    def test_stranger_does_not_see_the_message(self):
        self.client.force_login(self.stranger)
        resp = self.client.get(reverse('ad_detail', args=[self.ad.pk]))
        self.assertNotContains(resp, 'Yetkazib berasizmi bugun?')

    def test_delete_from_inquiries_page_returns_there(self):
        self.client.force_login(self.seller)
        resp = self.client.post(reverse('inquiry_delete', args=[self.inq.pk]),
                                {'next': 'inquiries'}, follow=True)
        self.assertEqual(resp.redirect_chain[-1][0], reverse('my_inquiries'))
        self.assertFalse(AdInquiry.objects.filter(pk=self.inq.pk).exists())
