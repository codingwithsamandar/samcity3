"""Maxsus rate-throttle klasslari (auth/OTP xavfsizligi uchun).

IP bo'yicha standart throttle yetarli emas, chunki bitta telefon raqamiga
ko'p IP'dan OTP yuborish (SMS-bombing) mumkin. Quyidagi throttle so'rovdagi
telefon raqami bo'yicha cheklaydi — bir raqamga belgilangan vaqtda faqat
cheklangan miqdorda kod yuboriladi.
"""
import re

from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle


_DIGITS = re.compile(r'\D+')


class CheckoutThrottle(UserRateThrottle):
    """Buyurtma rasmiylashtirishni cheklaydi (DEFAULT_THROTTLE_RATES['checkout'])."""
    scope = 'checkout'


class PaymentInitThrottle(UserRateThrottle):
    """To'lovni boshlash so'rovini cheklaydi (DEFAULT_THROTTLE_RATES['payment_init'])."""
    scope = 'payment_init'


class PhoneSendThrottle(SimpleRateThrottle):
    """OTP yuborish — telefon raqami bo'yicha cheklov (DEFAULT_THROTTLE_RATES['otp_send'])."""
    scope = 'otp_send'

    def get_cache_key(self, request, view):
        phone = (request.data or {}).get('phone', '')
        phone = _DIGITS.sub('', str(phone))
        if not phone:
            # Telefon berilmagan bo'lsa — IP bo'yicha cheklaymiz (baribir himoya).
            phone = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': phone}
