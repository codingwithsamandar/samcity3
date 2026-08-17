from django.urls import path
from . import views

app_name = 'places'

urlpatterns = [
    path('', views.map_view, name='map'),
    path('directory/', views.place_list, name='place_list'),
    path('nearby/', views.nearby, name='nearby'),
    path('geojson/', views.places_geojson, name='geojson'),
    path('search/', views.search_api, name='search_api'),
    path('neighborhoods/', views.neighborhoods_geojson, name='neighborhoods_geojson'),
    path('neighborhoods/<int:pk>/', views.neighborhood_detail, name='neighborhood_detail'),
    path('neighborhoods/<int:pk>/geojson/', views.neighborhood_places_geojson, name='neighborhood_places_geojson'),
    path('api/route/', views.route_api, name='route'),
    path('api/reverse-geocode/', views.reverse_geocode_api, name='reverse_geocode'),
    path('add/', views.place_create, name='place_create'),
    path('favorites/', views.my_favorite_places, name='my_favorites'),
    path('<int:pk>/review/', views.place_review, name='place_review'),
    path('<int:pk>/favorite/', views.place_favorite_toggle, name='place_favorite'),

    # Phase 4/5 — toifa bo'yicha bo'limlar (place_list ni qayta ishlatadi)
    path('tourism/', views.place_list, {'category': 'tourist'}, name='tourism_list'),

    path('<int:pk>/', views.place_detail, name='place_detail'),
    path('<int:pk>/edit/', views.place_edit, name='place_edit'),
    path('<int:pk>/menu/', views.place_menu, name='place_menu'),
    path('<int:pk>/menu/add/', views.menu_item_add, name='menu_item_add'),
    path('menu/<int:item_id>/delete/', views.menu_item_delete, name='menu_item_delete'),
    path('<int:pk>/delete/', views.place_delete, name='place_delete'),
]
