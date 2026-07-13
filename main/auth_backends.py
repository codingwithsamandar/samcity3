"""Telefon formatiga moslashuvchan autentifikatsiya backend'i.

Bazada telefon raqami ikki xil ko'rinishda saqlanadi:
  - veb-ro'yxatdan o'tishda: '900123456' (9 xonali, prefiksisiz)
  - seed/import/API orqali:   '+998900123456' (xalqaro format)

Standart ModelBackend kiritilgan matnni aynan qidiradi, shuning uchun
foydalanuvchi raqamni "boshqacha" ko'rinishda kiritsa (yoki bazadagi format
boshqacha bo'lsa) kira olmaydi. Bu backend kiritilgan raqamning barcha
ehtimoliy ko'rinishlarini sinaydi — veb LoginView, admin va custom view'lar
uchun bir xil ishlaydi.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


def phone_candidates(raw):
    """Kiritilgan raqamdan ehtimoliy saqlash formatlarini qaytaradi (tartibli, takrorsiz)."""
    raw = (raw or '').strip()
    if not raw:
        return []
    digits = ''.join(ch for ch in raw if ch.isdigit())
    if not digits:
        return [raw]
    base = ('+' + digits) if raw.startswith('+') else digits
    out = [base]
    if len(digits) == 9:                      # '900123456'
        out += ['+998' + digits, '998' + digits]
    elif len(digits) == 12 and digits.startswith('998'):  # '998900123456'
        local = digits[3:]
        out += ['+' + digits, digits, local]
    # takrorsiz, lekin tartibni saqlagan holda
    seen, uniq = set(), []
    for c in out:
        if c and c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq


class PhoneModelBackend(ModelBackend):
    """USERNAME_FIELD=phone bo'yicha, format variantlarini sinab autentifikatsiya."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        # LoginView 'username' yuboradi; custom view 'phone' yuborishi mumkin.
        raw = username or kwargs.get('phone')
        if raw is None or password is None:
            return None
        for cand in phone_candidates(raw):
            try:
                user = User.objects.get(phone=cand)
            except User.DoesNotExist:
                continue
            except User.MultipleObjectsReturned:
                user = User.objects.filter(phone=cand).order_by('id').first()
            if user and user.check_password(password) and self.user_can_authenticate(user):
                return user
        # Bitta ham topilmasa, timing-attack himoyasi uchun bir marta hash hisoblaymiz
        User().set_password(password)
        return None
