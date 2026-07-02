"""
WebSocket consumer for live delivery tracking.

Room: ws/delivery/track/<order_id>/
Only the order's customer, the assigned driver, or staff may join.
The consumer is read-only for clients — coordinates are pushed by the
driver-location HTTP API (see views.driver_update_location), which broadcasts
into this room. Status changes are broadcast via signals/realtime helpers.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from .realtime import order_group, store_chat_group


class DeliveryTrackingConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.order_id = self.scope['url_route']['kwargs']['order_id']
        self.user = self.scope.get('user')
        self.group_name = order_group(self.order_id)

        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        order = await self.get_order()
        if not order or not self._can_view(order):
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send the current snapshot immediately so the map isn't empty.
        await self.send(text_data=json.dumps({
            'type': 'snapshot',
            'status': order['status'],
            'status_display': order['status_display'],
            'driver_name': order['driver_name'],
            'driver_phone': order['driver_phone'],
            'lat': order['lat'],
            'lng': order['lng'],
            'dest_lat': order['dest_lat'],
            'dest_lng': order['dest_lng'],
            'store_lat': order['store_lat'],
            'store_lng': order['store_lng'],
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Clients don't send anything meaningful; ignore inbound messages.
    async def receive(self, text_data=None, bytes_data=None):
        return

    # ── Group event handlers ──────────────────────────────────────
    async def tracking_location(self, event):
        await self.send(text_data=json.dumps({
            'type': 'location',
            'lat': event['lat'],
            'lng': event['lng'],
            'heading': event.get('heading'),
            'speed': event.get('speed'),
        }))

    async def tracking_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'status',
            'status': event['status'],
            'status_display': event['status_display'],
            'driver_name': event.get('driver_name', ''),
            'driver_phone': event.get('driver_phone', ''),
        }))

    # ── DB access ─────────────────────────────────────────────────
    def _can_view(self, order):
        return (
            order['user_id'] == self.user.id
            or (order['driver_user_id'] and order['driver_user_id'] == self.user.id)
            or self.user.is_staff
        )

    @database_sync_to_async
    def get_order(self):
        from .models import Order
        try:
            order = (
                Order.objects
                .select_related('driver__user', 'driver__location')
                .prefetch_related('items__product__store')
                .get(pk=self.order_id)
            )
        except (Order.DoesNotExist, ValueError):
            return None

        loc = None
        if order.driver:
            try:
                loc = order.driver.location  # reverse OneToOne may not exist
            except Exception:
                loc = None
        store = None
        first = order.items.first()
        if first and first.product and first.product.store:
            store = first.product.store

        return {
            'user_id': order.user_id,
            'driver_user_id': order.driver.user_id if order.driver else None,
            'status': order.status,
            'status_display': order.get_status_display(),
            'driver_name': order.driver.full_name if order.driver else '',
            'driver_phone': order.driver.phone if order.driver else '',
            'lat': loc.latitude if loc else None,
            'lng': loc.longitude if loc else None,
            'store_lat': store.latitude if store else None,
            'store_lng': store.longitude if store else None,
            # No per-order destination coords in schema yet — customer page can
            # use browser geolocation; these stay null for now.
            'dest_lat': None,
            'dest_lng': None,
        }


class StoreChatConsumer(AsyncWebsocketConsumer):
    """Mijoz ↔ do'kon chat xonasi.

    Room: ws/delivery/chat/<thread_id>/
    Faqat thread ishtirokchilari (mijoz yoki do'kon egasi) qo'shila oladi.
    Mijoz {type: message, text} yuboradi — xabar saqlanadi, guruhga broadcast
    qilinadi va qarshi tomonga bildirishnoma yuboriladi (delivery.chat).
    """

    async def connect(self):
        self.thread_id = self.scope['url_route']['kwargs']['thread_id']
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        thread = await self.get_thread()
        if not thread:
            await self.close()
            return
        self.group_name = store_chat_group(self.thread_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data or '{}')
        except (ValueError, TypeError):
            return
        if data.get('type') != 'message':
            return
        text = (data.get('text') or '').strip()
        if not text:
            return
        # Xabarni saqlash + broadcast + bildirishnoma (delivery.chat.create_message
        # push_chat_message orqali o'zi guruhga yuboradi).
        await self.save_message(text)

    # ── Group event handler ──
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'id': event['id'],
            'text': event['text'],
            'sender_id': event['sender_id'],
            'is_owner': event['is_owner'],
            'created_at': event['created_at'],
        }))

    # ── DB access ──
    @database_sync_to_async
    def get_thread(self):
        from .models import StoreChatThread
        from .chat import is_participant
        try:
            thread = StoreChatThread.objects.select_related('store').get(pk=self.thread_id)
        except (StoreChatThread.DoesNotExist, ValueError):
            return None
        return thread if is_participant(thread, self.user) else None

    @database_sync_to_async
    def save_message(self, text):
        from .models import StoreChatThread
        from .chat import create_message, is_participant
        try:
            thread = StoreChatThread.objects.select_related('store').get(pk=self.thread_id)
        except (StoreChatThread.DoesNotExist, ValueError):
            return
        if not is_participant(thread, self.user):
            return
        create_message(thread, self.user, text)
