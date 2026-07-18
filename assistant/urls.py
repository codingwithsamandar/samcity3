from django.urls import path
from . import views

app_name = 'assistant'

urlpatterns = [
    path('', views.page, name='page'),
    path('chat/', views.chat, name='chat'),
    path('tts/', views.tts, name='tts'),
]
