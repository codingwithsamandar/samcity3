"""Chat (mahalla chat) API view'lari.

Eslatma: real-vaqt yetkazib berish WebSocket (Channels) orqali amalga oshiriladi.
Bu REST endpoint'lar tarix va xabar yuborish uchun (mobil MVP). Real-time
ulanish keyingi bosqichda qo'shiladi.
"""
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import ChatRoom, ChatMessage, ChatMember, ChatAdmin
from .chat_serializers import ChatRoomSerializer, ChatMessageSerializer, SendMessageSerializer


def _is_admin(room, user):
    return ChatAdmin.objects.filter(neighborhood=room.neighborhood, user=user).exists()


class ChatRoomViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ChatRoomSerializer

    def get_queryset(self):
        return ChatRoom.objects.select_related('neighborhood').all()


class ChatMessagesView(APIView):
    """GET — xabarlar tarixi; POST — yangi xabar yuborish."""
    permission_classes = [IsAuthenticated]

    def _get_room(self, room_id):
        return ChatRoom.objects.select_related('neighborhood').filter(pk=room_id).first()

    def get(self, request, room_id):
        room = self._get_room(room_id)
        if room is None:
            return Response({'detail': 'Xona topilmadi.'}, status=404)

        # A'zolikni ta'minlash (yangi a'zo — kutilmoqda holatida)
        member, _ = ChatMember.objects.get_or_create(
            room=room, user=request.user,
            defaults={'is_approved': False, 'is_banned': False})
        if member.is_banned:
            return Response({'detail': 'Siz bu chatdan bloklangansiz.'}, status=403)

        # O'qilgan vaqtni yangilash
        ChatMember.objects.filter(pk=member.pk).update(
            last_read_at=timezone.now(), last_seen_at=timezone.now())

        qs = (room.messages.filter(is_deleted=False)
              .select_related('user', 'reply_to', 'reply_to__user')
              .order_by('-created_at'))

        # Oddiy sahifalash (eng yangi oldin) — limit/offset
        try:
            limit = min(int(request.query_params.get('limit', 50)), 100)
            offset = int(request.query_params.get('offset', 0))
        except ValueError:
            limit, offset = 50, 0
        total = qs.count()
        page = list(qs[offset:offset + limit])
        page.reverse()  # ekranda eski → yangi tartibida ko'rsatish uchun

        ser = ChatMessageSerializer(page, many=True, context={'request': request})
        return Response({
            'count': total,
            'can_write': member.is_approved or _is_admin(room, request.user),
            'my_status': 'approved' if member.is_approved else 'pending',
            'results': ser.data,
        })

    def post(self, request, room_id):
        room = self._get_room(room_id)
        if room is None:
            return Response({'detail': 'Xona topilmadi.'}, status=404)

        member, _ = ChatMember.objects.get_or_create(
            room=room, user=request.user,
            defaults={'is_approved': False, 'is_banned': False})
        if member.is_banned:
            return Response({'detail': 'Siz bu chatdan bloklangansiz.'}, status=403)

        is_admin = _is_admin(room, request.user)
        if not (member.is_approved or is_admin):
            return Response(
                {'detail': "Yozish uchun mahalla admini tasdig'i kerak."},
                status=status.HTTP_403_FORBIDDEN)

        ser = SendMessageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        text = ser.validated_data['text'].strip()
        if not text:
            return Response({'detail': "Xabar bo'sh bo'lishi mumkin emas."},
                            status=status.HTTP_400_BAD_REQUEST)

        reply_to = None
        rid = ser.validated_data.get('reply_to')
        if rid:
            reply_to = ChatMessage.objects.filter(pk=rid, room=room).first()

        msg = ChatMessage.objects.create(
            room=room, user=request.user, text=text,
            is_admin_message=is_admin, reply_to=reply_to,
        )
        return Response(
            ChatMessageSerializer(msg, context={'request': request}).data,
            status=status.HTTP_201_CREATED)
