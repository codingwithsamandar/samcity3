from django.urls import path
from . import views

urlpatterns = [
    path('', views.venue_list, name='venue_list'),
    path('create/', views.venue_create, name='venue_create'),
    path('<uuid:pk>/', views.venue_detail, name='venue_detail'),
    path('<uuid:pk>/edit/', views.venue_edit, name='venue_edit'),
    path('<uuid:pk>/delete/', views.venue_delete, name='venue_delete'),
    path('<uuid:pk>/book/', views.venue_book, name='venue_book'),
    path('<uuid:pk>/slots/', views.venue_slots, name='venue_slots'),
    path('<uuid:pk>/staff-at/', views.venue_staff_at, name='venue_staff_at'),
    path('<uuid:pk>/services/', views.venue_services, name='venue_services'),
    path('<uuid:pk>/services/add/', views.service_add, name='service_add'),
    path('<uuid:pk>/staff/add/', views.staff_add, name='staff_add'),
    path('service/<uuid:service_id>/delete/', views.service_delete, name='service_delete'),
    path('staff/<uuid:staff_id>/delete/', views.staff_delete, name='staff_delete'),
    path('my/', views.my_bookings, name='my_venue_bookings'),
    path('pay/<uuid:booking_id>/', views.booking_pay, name='booking_pay'),
    path('cancel/<uuid:booking_id>/', views.booking_cancel, name='booking_cancel'),
    path('manage/', views.manage_bookings, name='manage_bookings'),
    path('action/<uuid:booking_id>/<str:action>/', views.booking_action, name='venue_booking_action'),
]
