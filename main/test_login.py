"""Veb-login testi — telefon formati moslashuvchan bo'lishi kerak.

Bazada telefon ikki xil formatda saqlanadi: veb-ro'yxatdan '900123456'
(9-xonali), seed/API'dan '+998900123456'. Foydalanuvchi qaysi ko'rinishda
kiritmasin, tizim uni topa olishi shart.
"""
from django.core.cache import cache
from django.test import TestCase, Client
from django.urls import reverse

from main.models import User


class PhoneFormatLoginTest(TestCase):
    PASSWORD = 'demo12345'

    def setUp(self):
        cache.clear()  # login rate-limiter holati testlar orasida oqmasin

    def _login(self, entered, path='/login/'):
        c = Client()
        return c.post(path, {'username': entered, 'password': self.PASSWORD})

    def test_plus998_user_login_by_any_format(self):
        """+998 formatda saqlangan userga 3 xil kiritish bilan kirish."""
        User.objects.create_user(phone='+998900000010', password=self.PASSWORD,
                                 name='Aziz', is_active=True)
        for entered in ('900000010', '+998900000010', '998900000010'):
            resp = self._login(entered)
            self.assertEqual(resp.status_code, 302,
                             f"{entered!r} bilan kirish 302 bo'lishi kerak edi")
            self.assertIn('/profile/', resp['Location'])

    def test_nine_digit_user_login_by_any_format(self):
        """9-xonali formatda saqlangan userga 3 xil kiritish bilan kirish."""
        User.objects.create_user(phone='900000020', password=self.PASSWORD,
                                 name='Dilnoza', is_active=True)
        for entered in ('900000020', '+998900000020', '998900000020'):
            resp = self._login(entered)
            self.assertEqual(resp.status_code, 302,
                             f"{entered!r} bilan kirish 302 bo'lishi kerak edi")

    def test_accounts_login_view_also_flexible(self):
        """Veb-forma /accounts/login/ (Django LoginView) ga POST qiladi —
        u ham telefon formatiga moslashuvchan bo'lishi shart."""
        User.objects.create_user(phone='+998900000040', password=self.PASSWORD,
                                 name='Aziz', is_active=True)
        resp = self._login('900000040', path='/accounts/login/')
        self.assertEqual(resp.status_code, 302,
                         "/accounts/login/ ham 9-xonali kiritishni qabul qilishi kerak")

    def test_wrong_password_rejected(self):
        User.objects.create_user(phone='+998900000030', password=self.PASSWORD,
                                 name='X', is_active=True)
        resp = self._login('900000030')  # to'g'ri raqam, lekin...
        c = Client()
        bad = c.post(reverse('login'),
                     {'username': '900000030', 'password': 'NOTOGRI'})
        self.assertEqual(bad.status_code, 200)  # login sahifasida qoladi
