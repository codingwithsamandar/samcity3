from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(
        r'ws/delivery/track/(?P<order_id>[0-9a-f-]+)/$',
        consumers.DeliveryTrackingConsumer.as_asgi(),
    ),
]
