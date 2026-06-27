from django.urls import path
from . import views

app_name = 'taxi'

urlpatterns = [
    path('', views.taxi_home, name='home'),

    # ── Map / ride-hailing ───────────────────────────────────────────────────
    path('map/', views.taxi_map, name='map'),
    path('api/nearby-drivers/', views.taxi_nearby_drivers, name='nearby_drivers'),
    path('api/estimate/', views.taxi_estimate, name='estimate'),
    path('api/location/update/', views.taxi_update_location, name='update_location'),
    path('trip/<uuid:trip_id>/track/', views.taxi_track, name='trip_track'),

    path('service/<uuid:pk>/', views.service_detail, name='service_detail'),
    path('taxist/<uuid:pk>/', views.taxist_detail, name='taxist_detail'),

    # ── Buyurtma / sayohat / to'lov ──────────────────────────────────────────
    path('taxist/<uuid:taxist_pk>/order/', views.order_create, name='order_create'),
    path('trip/<uuid:trip_id>/pay/', views.trip_payment, name='trip_payment'),
    path('trip/<uuid:trip_id>/', views.trip_detail, name='trip_detail'),
    path('trips/', views.my_trips, name='my_trips'),

    # ── Haydovchi (taksist) o'zini ro'yxatdan o'tkazish / boshqarish ─────────────
    path('register/', views.taxist_register, name='taxist_register'),
    path('me/', views.taxist_manage, name='taxist_manage'),
    path('me/edit/', views.taxist_edit, name='taxist_edit'),
    path('me/route/add/', views.route_add, name='route_add'),
    path('me/route/<uuid:route_id>/delete/', views.route_delete, name='route_delete'),
]
