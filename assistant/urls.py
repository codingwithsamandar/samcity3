from django.urls import path
from . import views

app_name = 'assistant'

urlpatterns = [
    path('', views.page, name='page'),
    path('chat/', views.chat, name='chat'),
    path('tts/', views.tts, name='tts'),
    path('stt/', views.stt, name='stt'),
    # Tasdiq oqimi — LLM yaratadi, foydalanuvchi tasdiqlaydi (server bajaradi).
    path('confirm/<uuid:action_id>/', views.confirm_action, name='confirm'),
    path('cancel/<uuid:action_id>/', views.cancel_action, name='cancel'),
]
