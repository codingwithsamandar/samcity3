"""
Real-time helpers for delivery order tracking.

All functions are defensive: if no channel layer is configured (or it errors),
they fail silently so HTTP requests / signals never break because of websockets.
"""
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def order_group(order_id):
    return f'track_order_{order_id}'


ACTIVE_DELIVERY_STATUSES = ('assigned', 'picked_up', 'on_the_way')


def _send(group, payload):
    layer = get_channel_layer()
    if layer is None:
        return
    try:
        async_to_sync(layer.group_send)(group, payload)
    except Exception:
        # Never let a websocket broadcast failure break the request.
        pass


def push_order_status(order):
    """Broadcast an order status change to its tracking room."""
    driver = order.driver
    _send(order_group(order.id), {
        'type': 'tracking_status',
        'status': order.status,
        'status_display': order.get_status_display(),
        'driver_name': getattr(driver, 'full_name', '') if driver else '',
        'driver_phone': getattr(driver, 'phone', '') if driver else '',
    })


def push_driver_location(order_id, lat, lng, heading=None, speed=None):
    """Broadcast a driver's live coordinates to one order's tracking room."""
    _send(order_group(order_id), {
        'type': 'tracking_location',
        'lat': lat,
        'lng': lng,
        'heading': heading,
        'speed': speed,
    })


def push_driver_location_for_orders(order_ids, lat, lng, heading=None, speed=None):
    for oid in order_ids:
        push_driver_location(oid, lat, lng, heading, speed)


# ── STORE CHAT (mijoz ↔ do'kon) ─────────────────────────────────────────────────

def store_chat_group(thread_id):
    return f'store_chat_{thread_id}'


def push_chat_message(message):
    """Yangi chat xabarini thread guruhiga jonli yuboradi (best-effort)."""
    _send(store_chat_group(message.thread_id), {
        'type': 'chat_message',
        'id': message.id,
        'text': message.text,
        'sender_id': str(message.sender_id),
        'is_owner': message.sender_id == message.thread.store.owner_id,
        'created_at': message.created_at.isoformat(),
    })
