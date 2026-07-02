"""
SamCity mobil API — view'lar.
Auth (telefon + OTP + JWT) va E'lonlar (Ads) moduli.
"""
import logging
import random
import string
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.db.models import F
from django.utils import timezone

from rest_framework import status, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from main.models import User, OTPCode, Ad, AdFavorite
from sms.backends import send_sms
from telegrambot.delivery import try_send_telegram, telegram_connect_url
from .permissions import IsOwnerOrReadOnly
from .throttles import PhoneSendThrottle
from .serializers import (
    UserSerializer, RegisterSerializer, VerifyOTPSerializer, LoginSerializer,
    ResendOTPSerializer, AdListSerializer, AdDetailSerializer, AdCreateSerializer,
)

logger = logging.getLogger('shofirkon.security')
OTP_MAX_ATTEMPTS = 5
OTP_TTL_MINUTES = 10


def _issue_tokens(user):
    """Foydalanuvchi uchun JWT access + refresh token qaytaradi."""
    refresh = RefreshToken.for_user(user)
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


def _create_and_send_otp(phone):
    """6 xonali OTP yaratadi va yuboradi (Telegram ulangan bo'lsa Telegram, aks
    holda SMS shlyuzi orqali).

    Yuborish muvaffaqiyatsiz bo'lsa ham kod bazada saqlanadi (foydalanuvchi
    qayta yuborishni so'rashi mumkin); xato log'ga yoziladi.

    (code, channel) qaytaradi — channel: 'telegram' | 'sms'.
    """
    code = ''.join(random.choices(string.digits, k=6))
    OTPCode.objects.create(
        phone=phone, code=code,
        expires_at=timezone.now() + timedelta(minutes=OTP_TTL_MINUTES),
    )
    # Avval Telegram kanalini sinaymiz (raqam ulangan bo'lsa). Ulanmagan yoki
    # o'chiq bo'lsa — mavjud SMS oqimi o'zgarmasdan ishlaydi.
    if try_send_telegram(phone, code):
        return code, 'telegram'
    ok = send_sms(phone, f"SamCity tasdiqlash kodi: {code}")
    if not ok:
        logger.warning("OTP SMS yuborilmadi: phone=%s", phone)
    return code, 'sms'


# ─── Auth ─────────────────────────────────────────────────────────────────────
class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PhoneSendThrottle]  # bir raqamga ko'p OTP yuborishni cheklaydi

    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        phone = ser.validated_data['phone']
        User.objects.create_user(
            phone=phone,
            password=ser.validated_data['password'],
            name=ser.validated_data.get('name', '') or '',
            is_active=False,
        )
        code, channel = _create_and_send_otp(phone)
        data = {'detail': "Tasdiqlash kodi yuborildi.", 'phone': phone,
                'verification_channel': channel}
        # SMS orqali ketgan bo'lsa — Telegram'ni ulash tavsiyasini beramiz.
        if channel == 'sms':
            url = telegram_connect_url()
            if url:
                data['telegram_connect_url'] = url
        if settings.DEBUG:
            data['debug_code'] = code  # faqat development'da, tez sinov uchun
        return Response(data, status=status.HTTP_201_CREATED)


class ResendOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PhoneSendThrottle]  # qayta yuborishni ham raqam bo'yicha cheklaymiz

    def post(self, request):
        ser = ResendOTPSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        phone = ser.validated_data['phone']
        if not User.objects.filter(phone=phone, is_active=False).exists():
            return Response({'detail': "Bunday kutilayotgan ro'yxat topilmadi."},
                            status=status.HTTP_404_NOT_FOUND)
        code, channel = _create_and_send_otp(phone)
        data = {'detail': "Yangi kod yuborildi.", 'verification_channel': channel}
        if channel == 'sms':
            url = telegram_connect_url()
            if url:
                data['telegram_connect_url'] = url
        if settings.DEBUG:
            data['debug_code'] = code
        return Response(data)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'otp_verify'  # kodni taxmin qilishga (brute-force) qarshi

    def post(self, request):
        ser = VerifyOTPSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        phone = ser.validated_data['phone']
        code = ser.validated_data['code']

        otp = (OTPCode.objects
               .filter(phone=phone, used=False, expires_at__gt=timezone.now())
               .order_by('-created_at').first())
        if not otp:
            return Response({'detail': "Kod muddati o'tgan. Qaytadan urinib ko'ring."},
                            status=status.HTTP_400_BAD_REQUEST)

        if otp.attempts >= OTP_MAX_ATTEMPTS:
            otp.used = True
            otp.save(update_fields=['used'])
            logger.warning("OTP lockout (API): phone=%s", phone)
            return Response({'detail': "Juda ko'p noto'g'ri urinish. Qaytadan ro'yxatdan o'ting."},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        if otp.code != code:
            otp.attempts = F('attempts') + 1
            otp.save(update_fields=['attempts'])
            otp.refresh_from_db(fields=['attempts'])
            remaining = max(0, OTP_MAX_ATTEMPTS - otp.attempts)
            return Response({'detail': f"Kod xato. Qolgan urinishlar: {remaining}."},
                            status=status.HTTP_400_BAD_REQUEST)

        otp.used = True
        otp.save(update_fields=['used'])
        user = User.objects.filter(phone=phone).first()
        if not user:
            return Response({'detail': "Foydalanuvchi topilmadi."},
                            status=status.HTTP_404_NOT_FOUND)
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=['is_active'])

        tokens = _issue_tokens(user)
        return Response({**tokens, 'user': UserSerializer(user, context={'request': request}).data})


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'  # parol brute-force'iga qarshi

    def post(self, request):
        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        phone = ser.validated_data['phone']
        password = ser.validated_data['password']

        user = authenticate(request, username=phone, password=password)
        if user is None:
            logger.warning("Failed API login: phone=%s", phone)
            return Response({'detail': "Telefon raqami yoki parol xato."},
                            status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return Response({'detail': "Hisob faollashtirilmagan. Avval OTP bilan tasdiqlang."},
                            status=status.HTTP_403_FORBIDDEN)

        tokens = _issue_tokens(user)
        return Response({**tokens, 'user': UserSerializer(user, context={'request': request}).data})


class MeView(RetrieveUpdateAPIView):
    """Joriy foydalanuvchi profili (GET / PATCH)."""
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


# ─── Ads ──────────────────────────────────────────────────────────────────────
class AdViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filterset_fields = ['category', 'price_type']
    search_fields = ['title', 'description', 'location']
    ordering_fields = ['created_at', 'price', 'views']
    ordering = ['-is_boosted', '-created_at']

    def get_queryset(self):
        qs = (Ad.objects.filter(status='active')
              .select_related('user').prefetch_related('images'))
        return qs

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'favorites':
            return AdListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return AdCreateSerializer
        return AdDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        Ad.objects.filter(pk=instance.pk).update(views=F('views') + 1)
        instance.refresh_from_db(fields=['views'])
        ser = AdDetailSerializer(instance, context={'request': request})
        return Response(ser.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def mine(self, request):
        qs = (Ad.objects.filter(user=request.user)
              .exclude(status='deleted')
              .select_related('user').prefetch_related('images')
              .order_by('-created_at'))
        page = self.paginate_queryset(qs)
        ser = AdListSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(ser.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def favorites(self, request):
        qs = (Ad.objects.filter(favorited_by__user=request.user, status='active')
              .select_related('user').prefetch_related('images')
              .order_by('-favorited_by__created_at'))
        page = self.paginate_queryset(qs)
        ser = AdListSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(ser.data)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        ad = self.get_object()
        if request.method == 'DELETE':
            AdFavorite.objects.filter(ad=ad, user=request.user).delete()
            return Response({'favorited': False})
        AdFavorite.objects.get_or_create(ad=ad, user=request.user)
        return Response({'favorited': True}, status=status.HTTP_201_CREATED)
