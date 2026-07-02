from django.urls import path
from . import views, cart_views

app_name = 'delivery'

urlpatterns = [
    # ── Store ─────────────────────────────────────────────────────────────────
    path('', views.store_list_view, name='store_list'),
    path('<int:pk>/', views.store_detail_view, name='store_detail'),

    # ── Product ───────────────────────────────────────────────────────────────
    path('<int:store_pk>/product/<int:product_pk>/', views.product_detail_view, name='product_detail'),

    # ── Cart page ─────────────────────────────────────────────────────────────
    path('cart/', views.cart_view, name='cart'),

    # ── Checkout / buyurtma ─────────────────────────────────────────────────────
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.my_orders, name='my_orders'),
    path('order/<uuid:order_id>/', views.order_detail, name='order_detail'),

    # ── Real-time tracking ──────────────────────────────────────────────────────
    path('order/<uuid:order_id>/track/', views.order_track, name='order_track'),
    path('order/<uuid:order_id>/confirm-pickup/', views.order_confirm_pickup, name='order_confirm_pickup'),
    path('driver/location/update/', views.driver_update_location, name='driver_update_location'),

    # ── Store / Product management (egasi) ──────────────────────────────────────
    path('stores/my/', views.my_stores, name='my_stores'),
    path('stores/create/', views.store_create, name='store_create'),
    path('store/<int:pk>/edit/', views.store_edit, name='store_edit'),
    path('store/<int:pk>/delete/', views.store_delete, name='store_delete'),
    path('store/<int:pk>/announce/', views.store_announcement_create, name='store_announcement_create'),
    path('store/<int:pk>/subscribe/', views.store_subscribe_toggle, name='store_subscribe_toggle'),

    # ── Do'kon bilan chat (mijoz ↔ do'kon) ──────────────────────────────────────
    path('chat/store/<int:store_pk>/start/', views.store_chat_start, name='store_chat_start'),
    path('chat/thread/<int:thread_id>/', views.store_chat_thread, name='store_chat_thread'),
    path('chat/thread/<int:thread_id>/send/', views.store_chat_send, name='store_chat_send'),
    path('chat/inbox/', views.store_chat_inbox, name='store_chat_inbox'),
    path('store/<int:store_pk>/product/create/', views.product_create, name='product_create'),
    path('product/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('product/<int:pk>/delete/', views.product_delete, name='product_delete'),

    # ── Store order dashboard (egasi) ───────────────────────────────────────────
    path('manage/orders/', views.store_orders, name='store_orders'),
    path('manage/order/<uuid:order_id>/status/', views.store_order_status, name='store_order_status'),

    # ── Delivery driver (haydovchi) ─────────────────────────────────────────────
    path('driver/register/', views.driver_register, name='driver_register'),
    path('driver/', views.driver_dashboard, name='driver_dashboard'),
    path('driver/profile/', views.driver_profile, name='driver_profile'),
    path('driver/available/', views.driver_toggle_available, name='driver_toggle_available'),
    path('order/<uuid:order_id>/accept/', views.order_accept, name='order_accept'),
    path('order/<uuid:order_id>/release/', views.order_release, name='order_release'),
    path('order/<uuid:order_id>/dstatus/', views.driver_order_status, name='driver_order_status'),

    # ── Cart actions ──────────────────────────────────────────────────────────
    path('cart/add/<int:product_pk>/',      cart_views.cart_add,      name='cart_add'),
    path('cart/remove/<int:product_pk>/',   cart_views.cart_remove,   name='cart_remove'),
    path('cart/increase/<int:product_pk>/', cart_views.cart_increase, name='cart_increase'),
    path('cart/decrease/<int:product_pk>/', cart_views.cart_decrease, name='cart_decrease'),
]
