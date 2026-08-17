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


class VerifyOtpTest(TestCase):
    """OTP tasdiqlash — ro'yxatdan o'tishning oxirgi qadami.

    `verify_otp` parolni tekshirmaydi (kod bo'yicha tasdiqlaydi), shuning uchun
    `authenticate()` chaqirilmaydi va `user.backend` o'rnatilmagan bo'ladi.
    Bir nechta AUTHENTICATION_BACKENDS sozlangani uchun `login()` ga backend
    ANIQ berilmasa ValueError chiqadi va ro'yxatdan o'tish uziladi.
    """
    PASSWORD = 'demo12345'

    def setUp(self):
        cache.clear()  # otp_verify rate-limiter holati oqmasin

    def _pending(self, phone):
        """Ro'yxatdan o'tish holatini tayyorlaydi: nofaol user + faol OTP + sessiya."""
        from datetime import timedelta
        from django.utils import timezone
        from main.models import OTPCode
        user = User.objects.create_user(phone=phone, password=self.PASSWORD,
                                        name='Yangi', is_active=False)
        OTPCode.objects.create(phone=phone, code='123456',
                               expires_at=timezone.now() + timedelta(minutes=10))
        c = Client()
        s = c.session
        s['pending_phone'] = phone
        s.save()
        return c, user

    def test_correct_otp_logs_user_in(self):
        c, user = self._pending('+998900000050')
        resp = c.post(reverse('verify_otp'), {'code': '123456'})
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/profile/', resp['Location'])
        # Hisob faollashdi VA sessiyaga kirdi
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(str(c.session.get('_auth_user_id')), str(user.pk))

    def test_wrong_otp_stays_on_page(self):
        c, user = self._pending('+998900000051')
        resp = c.post(reverse('verify_otp'), {'code': '000000'})
        self.assertEqual(resp.status_code, 200)  # sahifada qoladi
        user.refresh_from_db()
        self.assertFalse(user.is_active)         # faollashmaydi
        self.assertIsNone(c.session.get('_auth_user_id'))  # kirmaydi
