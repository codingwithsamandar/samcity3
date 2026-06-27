from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/taxi/track/(?P<trip_id>[0-9a-f-]+)/$', consumers.TaxiTrackingConsumer.as_asgi()),
]
