from django.urls import path
from . import views

app_name = 'places'

urlpatterns = [
    path('', views.map_view, name='map'),
    path('directory/', views.place_list, name='place_list'),
    path('nearby/', views.nearby, name='nearby'),
    path('geojson/', views.places_geojson, name='geojson'),
    path('api/route/', views.route_api, name='route'),
    path('api/reverse-geocode/', views.reverse_geocode_api, name='reverse_geocode'),
    path('add/', views.place_create, name='place_create'),
    path('favorites/', views.my_favorite_places, name='my_favorites'),
    path('<int:pk>/review/', views.place_review, name='place_review'),
    path('<int:pk>/favorite/', views.place_favorite_toggle, name='place_favorite'),

    # Phase 4/5 — toifa bo'yicha bo'limlar (place_list ni qayta ishlatadi)
    path('tourism/', views.place_list, {'category': 'tourist'}, name='tourism_list'),
    path('furniture/', views.place_list, {'category': 'furniture'}, name='furniture_list'),
    path('electronics/', views.place_list, {'category': 'electronics'}, name='electronics_list'),

    path('<int:pk>/', views.place_detail, name='place_detail'),
    path('<int:pk>/edit/', views.place_edit, name='place_edit'),
    path('<int:pk>/delete/', views.place_delete, name='place_delete'),
]
