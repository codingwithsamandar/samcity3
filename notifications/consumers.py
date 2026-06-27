"""
Per-user notification WebSocket.

Room: ws/notifications/  — each authenticated user joins their private group
`notif_user_<id>`. New notifications are pushed by notifications.models.notify().
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


def user_group(user_id):
    return f'notif_user_{user_id}'


class NotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        self.group_name = user_group(self.user.id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'unread', 'count': await self.unread_count(),
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data or '{}')
        except (ValueError, TypeError):
            return
        if data.get('type') == 'mark_all_read':
            await self.mark_all_read()
            await self.send(text_data=json.dumps({'type': 'unread', 'count': 0}))

    # ── Group event handler ──
    async def notify_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'text': event['text'],
            'url': event.get('url', ''),
            'category': event.get('category', 'system'),
            'icon': event.get('icon', '🔔'),
            'count': event.get('count', 0),
        }))

    @database_sync_to_async
    def unread_count(self):
        return self.user.notifications.filter(is_read=False).count()

    @database_sync_to_async
    def mark_all_read(self):
        self.user.notifications.filter(is_read=False).update(is_read=True)
