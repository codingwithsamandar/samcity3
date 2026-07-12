"""Hokim paneli (tuman e'loni) testlari — scoping, ruxsat, broadcast."""
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APIClient

from main.models import (
    User, District, Neighborhood, DistrictAdmin, DistrictAnnouncement,
    ChatRoom, ChatMember, ChatAdmin, NeighborhoodAnnouncement,
)
from notifications.models import Notification


class HokimPanelTest(TestCase):
    def setUp(self):
        # Ikki tuman
        self.shofirkon = District.objects.create(name='Shofirkon tumani')
        self.other = District.objects.create(name='Buxoro tumani')

        # Shofirkon ichida 2 mahalla, boshqa tumanda 1 mahalla
        self.mah_a = Neighborhood.objects.create(name='Mahalla A', district=self.shofirkon)
        self.mah_b = Neighborhood.objects.create(name='Mahalla B', district=self.shofirkon)
        self.mah_x = Neighborhood.objects.create(name='Mahalla X', district=self.other)

        # Aholi: 2 tasi Shofirkonni (A va B), 1 tasi boshqa tumanni, 1 tasi mahallasiz
        self.res_a = User.objects.create_user(phone='+998900000001', password='x', neighborhood=self.mah_a)
        self.res_b = User.objects.create_user(phone='+998900000002', password='x', neighborhood=self.mah_b)
        self.res_other = User.objects.create_user(phone='+998900000003', password='x', neighborhood=self.mah_x)
        self.res_none = User.objects.create_user(phone='+998900000004', password='x')

        # Hokim — Shofirkon tumaniga tayinlangan (o'zi ham mahalla A aholisi)
        self.hokim = User.objects.create_user(phone='+998900000009', password='pass1234', neighborhood=self.mah_a)
        DistrictAdmin.objects.create(district=self.shofirkon, user=self.hokim)

        self.client = Client()

    def test_hokim_can_post_and_only_district_residents_notified(self):
        self.client.force_login(self.hokim)
        resp = self.client.post(
            reverse('district_announce', args=[self.shofirkon.pk]),
            {'title': 'Suv o‘chadi', 'text': 'Ertaga 9:00-15:00 suv bo‘lmaydi.'},
        )
        self.assertEqual(resp.status_code, 302)

        # E'lon yaratildi
        ann = DistrictAnnouncement.objects.get(district=self.shofirkon)
        self.assertEqual(ann.created_by, self.hokim)

        # Shofirkon aholisi (res_a, res_b) bildirishnoma oldi
        self.assertEqual(Notification.objects.filter(recipient=self.res_a).count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.res_b).count(), 1)
        # Boshqa tuman aholisi va mahallasiz — OLMADI
        self.assertEqual(Notification.objects.filter(recipient=self.res_other).count(), 0)
        self.assertEqual(Notification.objects.filter(recipient=self.res_none).count(), 0)
        # Hokimning o'ziga yuborilmadi (exclude_user)
        self.assertEqual(Notification.objects.filter(recipient=self.hokim).count(), 0)
        # recipients_count = 2 (res_a, res_b)
        self.assertEqual(ann.recipients_count, 2)

    def test_non_hokim_cannot_post(self):
        self.client.force_login(self.res_a)  # oddiy aholi
        resp = self.client.post(
            reverse('district_announce', args=[self.shofirkon.pk]),
            {'title': 'Ruxsatsiz', 'text': 'Bo‘lmaydi'},
        )
        self.assertEqual(resp.status_code, 302)  # xatolik bilan redirect
        self.assertEqual(DistrictAnnouncement.objects.count(), 0)
        self.assertEqual(Notification.objects.count(), 0)

    def test_panel_visible_to_hokim_only(self):
        # Hokim ko'radi
        self.client.force_login(self.hokim)
        self.assertEqual(self.client.get(reverse('hokim_panel')).status_code, 200)
        # Oddiy aholi — redirect (ruxsat yo'q)
        self.client.force_login(self.res_a)
        self.assertEqual(self.client.get(reverse('hokim_panel')).status_code, 302)

    def test_staff_is_admin_of_all_districts(self):
        staff = User.objects.create_user(phone='+998900000010', password='x', is_staff=True)
        self.client.force_login(staff)
        resp = self.client.post(
            reverse('district_announce', args=[self.other.pk]),
            {'title': 'Staff e‘lon', 'text': 'Butun Buxoro tumaniga'},
        )
        self.assertEqual(resp.status_code, 302)
        ann = DistrictAnnouncement.objects.get(district=self.other)
        # Buxoro tumanida faqat res_other bor
        self.assertEqual(ann.recipients_count, 1)
        self.assertEqual(Notification.objects.filter(recipient=self.res_other).count(), 1)

    # ── Mobil API (hokim paneli) ──
    def test_mobile_api_panel_and_announce(self):
        api = APIClient()
        api.force_authenticate(self.hokim)
        # Panel — hokim 1 ta tumanni ko'radi
        r = api.get('/api/hokim/')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data['is_hokim'])
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['district']['residents_count'], 3)

        # E'lon joylash → tuman aholisiga push
        r = api.post(f'/api/hokim/{self.shofirkon.pk}/announce/',
                     {'title': 'Mobil e‘lon', 'text': 'Test'})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['recipients_count'], 2)
        self.assertEqual(Notification.objects.filter(recipient=self.res_a).count(), 1)

    def test_mobile_api_announce_with_image(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        # 1x1 PNG
        png = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
               b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00'
               b'\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
        img = SimpleUploadedFile('e.png', png, content_type='image/png')
        api = APIClient()
        api.force_authenticate(self.hokim)
        r = api.post(f'/api/hokim/{self.shofirkon.pk}/announce/',
                     {'title': 'Rasmli', 'text': 'Test', 'image': img}, format='multipart')
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.data['image'])  # rasm URL qaytdi
        ann = DistrictAnnouncement.objects.get(title='Rasmli')
        self.assertTrue(bool(ann.image))
        self.assertEqual(ann.recipients_count, 2)

    def test_mobile_api_non_hokim_forbidden(self):
        api = APIClient()
        api.force_authenticate(self.res_a)
        self.assertFalse(api.get('/api/hokim/').data['is_hokim'])
        r = api.post(f'/api/hokim/{self.shofirkon.pk}/announce/',
                     {'title': 'x', 'text': 'y'})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(DistrictAnnouncement.objects.count(), 0)


class AdminCreatedAnnouncementTest(TestCase):
    """Django admin orqali yaratilgan e'lon ham aholiga bildirishnoma yuborsin."""

    def setUp(self):
        self.d = District.objects.create(name='Admin tuman')
        self.nb = Neighborhood.objects.create(name='Admin mahalla', district=self.d)
        self.res = User.objects.create_user(phone='+998944440001', password='x',
                                            neighborhood=self.nb)
        self.superuser = User.objects.create_user(phone='+998944449999', password='x',
                                                  is_staff=True)
        self.superuser.is_superuser = True
        self.superuser.save()
        self.client = Client()
        self.client.force_login(self.superuser)

    def test_admin_neighborhood_announcement_notifies(self):
        resp = self.client.post('/admin/main/neighborhoodannouncement/add/', {
            'neighborhood': self.nb.pk, 'title': 'Admin orqali', 'text': 'Matn',
        }, HTTP_HOST='127.0.0.1')
        self.assertEqual(resp.status_code, 302)  # saqlandi
        self.assertTrue(NeighborhoodAnnouncement.objects.filter(title='Admin orqali').exists())
        self.assertEqual(Notification.objects.filter(recipient=self.res).count(), 1)

    def test_admin_district_announcement_notifies(self):
        resp = self.client.post('/admin/main/districtannouncement/add/', {
            'district': self.d.pk, 'title': 'Tuman admin', 'text': 'Matn',
        }, HTTP_HOST='127.0.0.1')
        self.assertEqual(resp.status_code, 302)
        ann = DistrictAnnouncement.objects.get(title='Tuman admin')
        self.assertEqual(ann.recipients_count, 1)
        self.assertEqual(Notification.objects.filter(recipient=self.res).count(), 1)

    def test_admin_edit_does_not_resend(self):
        # Tahrirlashda qayta yuborilmasin (faqat yangi yaratishda).
        self.client.post('/admin/main/neighborhoodannouncement/add/', {
            'neighborhood': self.nb.pk, 'title': 'Bir marta', 'text': 'Matn',
        }, HTTP_HOST='127.0.0.1')
        ann = NeighborhoodAnnouncement.objects.get(title='Bir marta')
        self.client.post(f'/admin/main/neighborhoodannouncement/{ann.pk}/change/', {
            'neighborhood': self.nb.pk, 'title': 'Bir marta (tahrir)', 'text': 'Matn2',
        }, HTTP_HOST='127.0.0.1')
        self.assertEqual(Notification.objects.filter(recipient=self.res).count(), 1)


class MahallaHokimAppointmentTest(TestCase):
    """Mahalla qo'shilgan payt hokim (ChatAdmin) admin inline orqali tayinlanadi."""

    def setUp(self):
        self.superuser = User.objects.create_user(
            phone='+998933330001', password='x', is_staff=True)
        self.superuser.is_superuser = True
        self.superuser.save()
        self.hokim = User.objects.create_user(phone='+998933330002', password='x')
        self.client = Client()
        self.client.force_login(self.superuser)

    def test_appoint_hokim_when_creating_mahalla(self):
        resp = self.client.post('/admin/main/neighborhood/add/', {
            'name': 'Yangi mahalla',
            'color': '#3551d1',
            'admins-TOTAL_FORMS': '1',
            'admins-INITIAL_FORMS': '0',
            'admins-MIN_NUM_FORMS': '0',
            'admins-MAX_NUM_FORMS': '1000',
            'admins-0-user': str(self.hokim.pk),
        }, HTTP_HOST='127.0.0.1')
        self.assertEqual(resp.status_code, 302)  # saqlandi
        nb = Neighborhood.objects.get(name='Yangi mahalla')
        # Hokim tayinlandi → u mahalla admini bo'ldi (rasmiy e'lon joylay oladi)
        self.assertTrue(ChatAdmin.objects.filter(neighborhood=nb, user=self.hokim).exists())
        self.assertTrue(nb.is_admin(self.hokim))


class MahallaAnnouncementRecipientsTest(TestCase):
    """Mahalla e'loni AYNAN residents'ga boradi (chat a'zoligiga bog'liq emas)."""

    def setUp(self):
        self.nb = Neighborhood.objects.create(name='Mahalla R')
        self.room = ChatRoom.objects.create(neighborhood=self.nb)
        # resident: mahallani tanlagan, LEKIN chatga a'zo EMAS
        self.resident = User.objects.create_user(phone='+998955000001', password='x', neighborhood=self.nb)
        # chat_only: chatga a'zo, LEKIN bu mahallani tanlaMAGAN
        self.chat_only = User.objects.create_user(phone='+998955000002', password='x')
        ChatMember.objects.create(room=self.room, user=self.chat_only, is_approved=True)
        # admin (rais)
        self.admin_user = User.objects.create_user(phone='+998955000009', password='x')
        ChatAdmin.objects.create(neighborhood=self.nb, user=self.admin_user)
        self.client = Client()

    def test_announcement_goes_to_residents_not_chat_members(self):
        self.client.force_login(self.admin_user)
        resp = self.client.post(
            reverse('mahalla_announce', args=[self.nb.pk]),
            {'title': 'Tozalash', 'text': 'Shanba kuni hasharga chiqamiz.'},
            HTTP_HOST='127.0.0.1')
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(NeighborhoodAnnouncement.objects.filter(neighborhood=self.nb).exists())
        # resident (mahallani tanlagan) — OLDI
        self.assertEqual(Notification.objects.filter(recipient=self.resident).count(), 1)
        # chat_only (faqat chat a'zosi, mahallani tanlamagan) — OLMADI
        self.assertEqual(Notification.objects.filter(recipient=self.chat_only).count(), 0)
