"""Bildirishnomalar (notifications) API view'lari.

Real vaqtli yetkazib berish WebSocket (Channels) orqali amalga oshiriladi
(`notifications/consumers.py`). Bu REST endpoint'lar tarix, o'qilmaganlar soni
va o'qildi-belgilash uchun (mobil ilova uchun).
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import Notification, DeviceToken
from .notifications_serializers import NotificationSerializer, MarkReadSerializer


def _unread_count(user):
    return Notification.objects.filter(recipient=user, is_read=False).count()


class NotificationListView(APIView):
    """GET — foydalanuvchining bildirishnomalari (eng yangi oldin).

    So'rov parametrlari: limit (≤100), offset, unread=1 (faqat o'qilmaganlar).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.filter(recipient=request.user)
        if request.query_params.get('unread') in ('1', 'true', 'True'):
            qs = qs.filter(is_read=False)

        try:
            limit = min(int(request.query_params.get('limit', 30)), 100)
            offset = max(int(request.query_params.get('offset', 0)), 0)
        except (ValueError, TypeError):
            limit, offset = 30, 0

        total = qs.count()
        page = qs[offset:offset + limit]
        ser = NotificationSerializer(page, many=True, context={'request': request})
        return Response({
            'count': total,
            'unread': _unread_count(request.user),
            'results': ser.data,
        })


class NotificationUnreadCountView(APIView):
    """GET — o'qilmagan bildirishnomalar soni (qo'ng'iroq badge'i uchun)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'unread': _unread_count(request.user)})


class NotificationMarkReadView(APIView):
    """POST — bildirishnomalarni o'qildi qilish.

    Tana: {"ids": [1, 2, 3]} — tanlanganlarni; tana bo'sh yoki ids berilmasa —
    barchasini o'qildi qiladi.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = MarkReadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ids = ser.validated_data.get('ids')

        qs = Notification.objects.filter(recipient=request.user, is_read=False)
        if ids:
            qs = qs.filter(id__in=ids)
        updated = qs.update(is_read=True)

        return Response({
            'updated': updated,
            'unread': _unread_count(request.user),
        }, status=status.HTTP_200_OK)


class DeviceTokenView(APIView):
    """FCM qurilma tokenini ro'yxatga olish / o'chirish (mobil push uchun).

    POST   {"token": "...", "platform": "android|ios|web"} — saqlaydi/yangilaydi.
    DELETE {"token": "..."} — logout'da tokenni deaktivatsiya qiladi.

    Token boshqa foydalanuvchidan shu foydalanuvchiga o'tsa (bitta telefonda
    akkaunt almashsa) — egasi yangilanadi.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = (request.data.get('token') or '').strip()
        platform = (request.data.get('platform') or 'android').strip().lower()
        if not token or len(token) > 255:
            return Response({'detail': 'token majburiy (≤255 belgi).'},
                            status=status.HTTP_400_BAD_REQUEST)
        if platform not in ('android', 'ios', 'web'):
            platform = 'android'
        obj, _created = DeviceToken.objects.update_or_create(
            token=token,
            defaults={'user': request.user, 'platform': platform, 'is_active': True},
        )
        return Response({'ok': True, 'id': obj.id}, status=status.HTTP_200_OK)

    def delete(self, request):
        token = (request.data.get('token') or '').strip()
        if not token:
            return Response({'detail': 'token majburiy.'},
                            status=status.HTTP_400_BAD_REQUEST)
        updated = DeviceToken.objects.filter(
            token=token, user=request.user,
        ).update(is_active=False)
        return Response({'ok': True, 'deactivated': updated}, status=status.HTTP_200_OK)
