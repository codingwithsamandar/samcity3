"""Do'kon xodimi bilan chat — mobil API view'lari.

Real-time yetkazish WebSocket (delivery.consumers.StoreChatConsumer) orqali;
bu REST endpoint'lar thread ochish, tarix va xabar yuborish uchun.
"""
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from delivery.models import Store, StoreChatThread
from delivery.chat import get_or_create_thread, is_participant, create_message
from .chat_store_serializers import (
    StoreChatThreadSerializer, StoreChatMessageSerializer,
)


class StoreChatStartView(APIView):
    """POST /stores/<store_pk>/chat/ — mijoz do'kon bilan suhbatni ochadi."""
    permission_classes = [IsAuthenticated]

    def post(self, request, store_pk):
        store = Store.objects.filter(pk=store_pk, is_active=True).first()
        if store is None:
            return Response({'detail': "Do'kon topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        if store.owner_id == request.user.id:
            return Response({'detail': "O'z do'koningiz bilan suhbat ocholmaysiz."},
                            status=status.HTTP_400_BAD_REQUEST)
        thread = get_or_create_thread(store, request.user)
        return Response(StoreChatThreadSerializer(thread, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)


class StoreChatThreadView(APIView):
    """GET — xabarlar tarixi; POST {text} — xabar yuborish (ishtirokchi bo'lsa)."""
    permission_classes = [IsAuthenticated]

    def _thread(self, request, thread_id):
        thread = (StoreChatThread.objects
                  .select_related('store', 'customer').filter(pk=thread_id).first())
        if thread is None or not is_participant(thread, request.user):
            return None
        return thread

    def get(self, request, thread_id):
        thread = self._thread(request, thread_id)
        if thread is None:
            return Response({'detail': 'Suhbat topilmadi.'}, status=status.HTTP_404_NOT_FOUND)
        # Qarshi tomon xabarlarini o'qilgan deb belgilaymiz.
        thread.messages.exclude(sender=request.user).filter(is_read=False).update(is_read=True)
        msgs = thread.messages.all()
        return Response({
            'thread': StoreChatThreadSerializer(thread, context={'request': request}).data,
            'messages': StoreChatMessageSerializer(msgs, many=True, context={'request': request}).data,
        })

    def post(self, request, thread_id):
        thread = self._thread(request, thread_id)
        if thread is None:
            return Response({'detail': 'Suhbat topilmadi.'}, status=status.HTTP_404_NOT_FOUND)
        text = (request.data.get('text') or '').strip()
        if not text:
            return Response({'detail': 'Xabar matni bo\'sh.'}, status=status.HTTP_400_BAD_REQUEST)
        msg = create_message(thread, request.user, text)
        return Response(StoreChatMessageSerializer(msg, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)


class StoreChatListView(APIView):
    """GET — foydalanuvchining suhbatlari (mijoz sifatida + do'kon egasi sifatida)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        threads = (StoreChatThread.objects
                   .filter(Q(customer=request.user) | Q(store__owner=request.user))
                   .select_related('store', 'customer')
                   .order_by('-updated_at'))
        return Response({
            'results': StoreChatThreadSerializer(
                threads, many=True, context={'request': request}).data,
        })
