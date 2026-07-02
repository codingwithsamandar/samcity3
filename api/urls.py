"""
SamCity mobil API marshrutlari.
Barchasi `/api/` prefiksi ostida (sdev/urls.py da ulanadi).
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .views import (
    RegisterView, VerifyOTPView, ResendOTPView, LoginView, MeView, AdViewSet,
)
from .delivery_views import (
    StoreViewSet, OrderViewSet, ProductDetailView, CartView,
    cart_add, cart_set, cart_remove, cart_clear, checkout,
    MyStoresView, MyStoreDetailView, StoreProductsView, StoreProductDetailView,
    StoreUpdatesView, StoreSubscribeToggleView, StoreAnnouncementCreateView,
    StoreOrdersView, StoreOrderStatusView, OrderConfirmPickupView,
)
from .taxi_views import TaxiServiceViewSet, TaxistViewSet, TripViewSet
from .chat_views import ChatRoomViewSet, ChatMessagesView
from .chat_store_views import (
    StoreChatStartView, StoreChatThreadView, StoreChatListView,
)
from .booking_views import VenueViewSet, VenueBookingViewSet
from .notifications_views import (
    NotificationListView, NotificationUnreadCountView, NotificationMarkReadView,
)
from .payment_views import InitiatePaymentView
from .health import HealthView, ReadyView
from .places_views import PlacesListView
from .community_views import PollListView, poll_vote, HelpListView
from .jobs_views import JobListView, ResumeListView
from .service_views import (
    ProvidersListView, CreateServicePaymentView, MyServicePaymentsView,
)

app_name = 'api'

router = DefaultRouter()
router.register('ads', AdViewSet, basename='ad')
router.register('stores', StoreViewSet, basename='store')
router.register('orders', OrderViewSet, basename='order')
router.register('taxi/services', TaxiServiceViewSet, basename='taxi-service')
router.register('taxi/taxists', TaxistViewSet, basename='taxist')
router.register('taxi/trips', TripViewSet, basename='trip')
router.register('chat/rooms', ChatRoomViewSet, basename='chat-room')
router.register('booking/venues', VenueViewSet, basename='venue')
router.register('booking/bookings', VenueBookingViewSet, basename='venue-booking')

auth_patterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('login/', LoginView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('me/', MeView.as_view(), name='me'),
]

cart_patterns = [
    path('', CartView.as_view(), name='cart'),
    path('add/', cart_add, name='cart-add'),
    path('set/', cart_set, name='cart-set'),
    path('remove/', cart_remove, name='cart-remove'),
    path('clear/', cart_clear, name='cart-clear'),
]

urlpatterns = [
    path('auth/', include(auth_patterns)),
    path('cart/', include(cart_patterns)),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('checkout/', checkout, name='checkout'),
    path('my/stores/', MyStoresView.as_view(), name='my-stores'),
    path('my/stores/<int:store_pk>/', MyStoreDetailView.as_view(), name='my-store-detail'),
    path('stores/<int:store_pk>/products/', StoreProductsView.as_view(), name='store-products'),
    path('stores/<int:store_pk>/products/<int:product_pk>/', StoreProductDetailView.as_view(), name='store-product-detail'),
    path('stores/<int:store_pk>/updates/', StoreUpdatesView.as_view(), name='store-updates'),
    path('stores/<int:store_pk>/subscribe/', StoreSubscribeToggleView.as_view(), name='store-subscribe'),
    path('stores/<int:store_pk>/announce/', StoreAnnouncementCreateView.as_view(), name='store-announce'),
    # Egasi buyurtma boshqaruvi + mijoz pickup tasdig'i
    path('my/orders/', StoreOrdersView.as_view(), name='my-orders'),
    path('my/orders/<uuid:order_id>/status/', StoreOrderStatusView.as_view(), name='my-order-status'),
    path('orders/<uuid:order_id>/confirm-pickup/', OrderConfirmPickupView.as_view(), name='order-confirm-pickup'),
    # Do'kon bilan chat (mijoz ↔ do'kon)
    path('stores/<int:store_pk>/chat/', StoreChatStartView.as_view(), name='store-chat-start'),
    path('delivery/chat/threads/', StoreChatListView.as_view(), name='store-chat-list'),
    path('delivery/chat/threads/<int:thread_id>/', StoreChatThreadView.as_view(), name='store-chat-thread'),
    path('chat/rooms/<int:room_id>/messages/', ChatMessagesView.as_view(), name='chat-messages'),
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('notifications/unread-count/', NotificationUnreadCountView.as_view(), name='notifications-unread-count'),
    path('notifications/read/', NotificationMarkReadView.as_view(), name='notifications-read'),
    path('payments/initiate/', InitiatePaymentView.as_view(), name='payments-initiate'),
    path('health/', HealthView.as_view(), name='health'),
    path('ready/', ReadyView.as_view(), name='ready'),
    path('places/', PlacesListView.as_view(), name='places'),
    path('community/polls/', PollListView.as_view(), name='polls'),
    path('community/polls/<uuid:poll_id>/vote/', poll_vote, name='poll-vote'),
    path('community/help/', HelpListView.as_view(), name='help'),
    path('jobs/', JobListView.as_view(), name='jobs'),
    path('resumes/', ResumeListView.as_view(), name='resumes'),
    path('service/providers/', ProvidersListView.as_view(), name='service-providers'),
    path('service/pay/', CreateServicePaymentView.as_view(), name='service-pay'),
    path('service/my/', MyServicePaymentsView.as_view(), name='service-my'),
    path('', include(router.urls)),
    # Hujjat (OpenAPI / Swagger)
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='docs'),
]
