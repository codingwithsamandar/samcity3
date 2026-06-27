"""Real-time helpers for taxi trip tracking (defensive — never break requests)."""
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def trip_group(trip_id):
    return f'taxi_trip_{trip_id}'


def _send(group, payload):
    layer = get_channel_layer()
    if layer is None:
        return
    try:
        async_to_sync(layer.group_send)(group, payload)
    except Exception:
        pass


def push_trip_location(trip_id, lat, lng):
    _send(trip_group(trip_id), {'type': 'trip_location', 'lat': lat, 'lng': lng})


def push_trip_status(trip):
    _send(trip_group(trip.id), {
        'type': 'trip_status',
        'status': trip.status,
        'status_display': trip.get_status_display(),
    })
