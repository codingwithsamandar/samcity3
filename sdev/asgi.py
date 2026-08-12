import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sdev.settings')

# Initialise Django before importing anything that touches models/consumers.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

from api.ws_auth import JWTAuthMiddleware

from django.conf import settings

import main.routing
import delivery.routing
import notifications.routing

websocket_urlpatterns = (
    main.routing.websocket_urlpatterns
    + delivery.routing.websocket_urlpatterns
    + notifications.routing.websocket_urlpatterns
)

# Taksi arxivlangan — ws/taxi/... socketlari faqat TAXI_ENABLED=True bo'lsa.
if settings.TAXI_ENABLED:
    import taxi.routing
    websocket_urlpatterns = websocket_urlpatterns + taxi.routing.websocket_urlpatterns

# AllowedHostsOriginValidator: faqat ALLOWED_HOSTS dagi domenlardan keladigan
# WebSocket ulanishlarini qabul qiladi (Cross-Site WebSocket Hijacking himoyasi).
application = ProtocolTypeRouter({
    'http': django_asgi_app,
    # Sessiya (web) avval, keyin JWT (mobil) — token bo'lsa foydalanuvchini almashtiradi.
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(JWTAuthMiddleware(URLRouter(websocket_urlpatterns)))
    ),
})
