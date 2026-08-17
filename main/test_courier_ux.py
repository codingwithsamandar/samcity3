"""Kuryer roliga moslashgan qobiq (nav / kirish nuqtasi / ish rejimi) testlari.

Bu testlar main/roles.py + context processor + base.html shartlarini birga
tekshiradi: bittasi uzilsa, kuryer ishga kirish yo'lini yo'qotadi.
"""
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from delivery.models import DeliveryDriver
from main.models import User


class CourierShellTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.plain = User.objects.create_user(phone='+998901112233', password='pass12345', name='Oddiy')
        cls.courier_user = User.objects.create_user(phone='+998904445566', password='pass12345', name='Kuryer')
        cls.driver = DeliveryDriver.objects.create(
            user=cls.courier_user, full_name='Kuryer Aka', phone='+998904445566',
        )

    def setUp(self):
        cache.clear()  # login rate-limiter holati testlar orasida oqmasin

    def test_oddiy_userga_kuryer_navigatsiyasi_korinmaydi(self):
        self.client.force_login(self.plain)
        html = self.client.get(reverse('home')).content.decode()
        self.assertNotIn('class="nav-work', html)
        self.assertNotIn('work-strip">', html)

    def test_kuryerga_nav_va_ish_chizigi_korinadi(self):
        self.client.force_login(self.courier_user)
        html = self.client.get(reverse('home')).content.decode()
        self.assertIn('class="nav-work', html)
        self.assertIn('work-strip', html)
        self.assertIn(reverse('delivery:driver_dashboard'), html)

    # Diqqat: reverse('login') — django.contrib.auth.urls dagi LoginView
    # (sdev/urls.py da 'accounts/' oldinroq ulangan). Veb-forma esa '/login/'
    # (main.views.user_login) ga POST qiladi — ikkala yo'l ham tekshiriladi.
    def test_kirishdan_keyin_kuryer_panelga_tushadi(self):
        resp = self.client.post('/login/', {'username': '+998904445566', 'password': 'pass12345'})
        self.assertRedirects(resp, reverse('delivery:driver_dashboard'))

    def test_kirishdan_keyin_oddiy_user_profilga_tushadi(self):
        resp = self.client.post('/login/', {'username': '+998901112233', 'password': 'pass12345'})
        self.assertRedirects(resp, reverse('profile'))

    def test_accounts_login_ham_kuryerni_panelga_yonaltiradi(self):
        resp = self.client.post(reverse('login'), {'username': '+998904445566', 'password': 'pass12345'})
        self.assertRedirects(resp, reverse('after_login'),
                             target_status_code=302)
        self.assertRedirects(self.client.get(reverse('after_login')),
                             reverse('delivery:driver_dashboard'))

    def test_panelda_ish_rejimi_yoqiladi(self):
        self.client.force_login(self.courier_user)
        html = self.client.get(reverse('delivery:driver_dashboard')).content.decode()
        self.assertIn('class="work-mode"', html)

    def test_bloklangan_kuryerga_yangi_buyurtma_soni_korsatilmaydi(self):
        self.driver.is_active = False
        self.driver.save(update_fields=['is_active'])
        self.client.force_login(self.courier_user)
        resp = self.client.get(reverse('home'))
        self.assertEqual(resp.context['courier_new_orders'], 0)
        self.assertTrue(resp.context['courier_blocked'])
