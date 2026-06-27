"""Taxi trip live-tracking WebSocket. Room: ws/taxi/track/<trip_id>/
Only the passenger or the assigned taxist (or staff) may join."""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from .realtime import trip_group


class TaxiTrackingConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.trip_id = self.scope['url_route']['kwargs']['trip_id']
        self.user = self.scope.get('user')
        self.group_name = trip_group(self.trip_id)
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        snap = await self.get_trip()
        if not snap or not self._can_view(snap):
            await self.close()
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'snapshot',
            'status': snap['status'], 'status_display': snap['status_display'],
            'lat': snap['lat'], 'lng': snap['lng'],
            'pickup': snap['pickup'], 'dest': snap['dest'],
            'taxist_name': snap['taxist_name'], 'taxist_phone': snap['taxist_phone'],
        }))

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        return

    async def trip_location(self, e):
        await self.send(text_data=json.dumps({'type': 'location', 'lat': e['lat'], 'lng': e['lng']}))

    async def trip_status(self, e):
        await self.send(text_data=json.dumps({'type': 'status', 'status': e['status'], 'status_display': e['status_display']}))

    def _can_view(self, snap):
        return (snap['passenger_id'] == self.user.id
                or (snap['taxist_user_id'] and snap['taxist_user_id'] == self.user.id)
                or self.user.is_staff)

    @database_sync_to_async
    def get_trip(self):
        from .models import Trip
        try:
            t = Trip.objects.select_related('taxist__user').get(pk=self.trip_id)
        except (Trip.DoesNotExist, ValueError):
            return None
        tx = t.taxist
        return {
            'passenger_id': t.passenger_id,
            'taxist_user_id': tx.user_id if tx else None,
            'status': t.status, 'status_display': t.get_status_display(),
            'lat': tx.latitude if tx else None, 'lng': tx.longitude if tx else None,
            'pickup': [t.pickup_lat, t.pickup_lng] if t.pickup_lat else None,
            'dest': [t.dest_lat, t.dest_lng] if t.dest_lat else None,
            'taxist_name': tx.full_name if tx else '',
            'taxist_phone': tx.phone if tx else '',
        }
