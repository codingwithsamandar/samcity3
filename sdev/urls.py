from django.conf import settings
from django.conf.urls.static import static
from django.urls import path,include
from django.contrib import admin

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    path('delivery/', include('delivery.urls', namespace='delivery')),
    path('taxi/', include('taxi.urls', namespace='taxi')),
    path('payments/', include('payments.urls', namespace='payments')),
    path('booking/', include('booking.urls')),
    path('notifications/', include('notifications.urls')),
    path('map/', include('places.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    # ── Mobil REST API (Flutter ilova) ──
    path('api/', include('api.urls', namespace='api')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

