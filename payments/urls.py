from django.urls import path
from . import views
from .payme import PaymeMerchantView
from .click import click_prepare, click_complete

app_name = 'payments'

urlpatterns = [
    path('', views.payments_home, name='home'),
    path('pay/<uuid:provider_pk>/', views.pay, name='pay'),
    path('receipt/<uuid:payment_id>/', views.receipt, name='receipt'),
    path('my/', views.my_payments, name='my_payments'),

    # ── To'lov shlyuzi webhook'lari (Payme / Click kabinetida ko'rsatiladi) ──
    path('payme/', PaymeMerchantView.as_view(), name='payme_callback'),
    path('click/prepare/', click_prepare, name='click_prepare'),
    path('click/complete/', click_complete, name='click_complete'),
]
