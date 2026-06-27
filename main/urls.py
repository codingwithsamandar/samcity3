from django.urls import path
from django.contrib.auth.views import LogoutView
from django.views.generic import RedirectView
from . import views
from . import community_views
from . import marketplace_views

class LogoutGetView(LogoutView):
    http_method_names = ['get', 'post']

urlpatterns = [
    # Asosiy
    path('', views.home, name='home'),
    path('app/', views.app_download, name='app_download'),
    path('register/', views.register, name='register'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('login/', views.user_login, name='login'),
    path('logout/', LogoutGetView.as_view(next_page='home'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('staff/analytics/', views.admin_dashboard, name='admin_dashboard'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/update/', views.profile_edit, name='profile_update'),
    path('profile/<uuid:pk>/', views.public_profile, name='public_profile'),

    # Barcha e'lonlar (login kerak emas)
    path('all-ads/', views.all_ads, name='all_ads'),

    # E'lonlar
    path('ads/', views.my_ads, name='my_ads'),
    path('ads/create/', views.ad_create, name='ad_create'),
    path('ads/new/', views.ad_create, name='ad_new'),
    path('ad/<uuid:pk>/', views.ad_detail, name='ad_detail'),
    path('ad/<uuid:pk>/edit/', views.ad_edit, name='ad_edit'),
    path('ad/<uuid:pk>/delete/', views.ad_delete, name='ad_delete'),
    path('ad/<uuid:pk>/toggle-sold/', views.ad_toggle_sold, name='ad_toggle_sold'),

    # Bron qilish
    path('ad/<uuid:pk>/book/', views.booking_create, name='booking_create'),
    path('bookings/', views.my_bookings, name='my_bookings'),
    path('bookings/received/', views.received_bookings, name='received_bookings'),
    path('bookings/<uuid:booking_id>/', views.booking_detail, name='booking_detail'),
    path('bookings/<uuid:booking_id>/<str:action>/', views.booking_action, name='booking_action'),

    # Mahalla chat
    path('neighborhood-chat/', views.neighborhood_chat, name='neighborhood_chat'),
    path('neighborhood-chat/<int:room_id>/', views.neighborhood_chat_room, name='neighborhood_chat_room'),
    path('api/chat/<int:room_id>/messages/', views.chat_messages_api, name='chat_messages_api'),
    path('api/chat/<int:room_id>/history/', views.chat_history, name='chat_history'),
    # Chat admin API
    path('api/chat/<int:room_id>/pending/', views.chat_pending_members, name='chat_pending_members'),
    path('api/chat/<int:room_id>/approve/<uuid:user_id>/', views.chat_approve_member, name='chat_approve_member'),
    path('api/chat/<int:room_id>/kick/<uuid:user_id>/', views.chat_kick_member, name='chat_kick_member'),
    path('api/chat/<int:room_id>/delete-msg/<int:msg_id>/', views.chat_delete_message, name='chat_delete_message'),
    path('api/chat/<int:room_id>/upload-image/', views.chat_upload_image, name='chat_upload_image'),

    # ─── GLOBAL SEARCH ──────────────────────────────────────────────────────
    path('search/', marketplace_views.global_search, name='global_search'),
    path('search/autocomplete/', marketplace_views.search_autocomplete, name='search_autocomplete'),

    # ─── MARKETPLACE (ad favorites / report / inquiry) ──────────────────────
    path('ads/saved/', marketplace_views.saved_ads, name='saved_ads'),
    path('ads/<uuid:pk>/favorite/', marketplace_views.ad_favorite_toggle, name='ad_favorite'),
    path('ads/<uuid:pk>/report/', marketplace_views.ad_report, name='ad_report'),
    path('ads/<uuid:pk>/inquiry/', marketplace_views.ad_inquiry, name='ad_inquiry'),
    path('ads/<uuid:pk>/contact/', marketplace_views.ad_contact_reveal, name='ad_contact_reveal'),

    # ─── COMMUNITY: POLLS ───────────────────────────────────────────────────
    path('community/polls/', community_views.poll_list, name='poll_list'),
    path('community/polls/create/', community_views.poll_create, name='poll_create'),
    path('community/polls/<uuid:poll_id>/', community_views.poll_detail, name='poll_detail'),
    path('community/polls/<uuid:poll_id>/vote/', community_views.poll_vote, name='poll_vote'),
    path('community/polls/<uuid:poll_id>/comment/', community_views.poll_comment, name='poll_comment'),

    # ─── COMMUNITY: MAHALLA MAP ─────────────────────────────────────────────
    path('community/map/', community_views.community_map, name='community_map'),
    path('community/map/geojson/', community_views.community_map_geojson, name='community_map_geojson'),

    # ─── COMMUNITY: HELP CENTER ─────────────────────────────────────────────
    path('community/help/', community_views.help_list, name='help_list'),
    path('community/help/create/', community_views.help_create, name='help_create'),
    path('community/help/<uuid:req_id>/', community_views.help_detail, name='help_detail'),
    path('community/help/<uuid:req_id>/volunteer/', community_views.help_volunteer, name='help_volunteer'),
    path('community/help/<uuid:req_id>/status/', community_views.help_status, name='help_status'),

    # ─── ISH E'LONLARI ───
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/create/', views.job_create, name='job_create'),
    path('jobs/<uuid:pk>/', views.job_detail, name='job_detail'),
    path('jobs/<uuid:pk>/edit/', views.job_edit, name='job_edit'),
    path('jobs/<uuid:pk>/delete/', views.job_delete, name='job_delete'),
    path('jobs/<uuid:pk>/close/', views.job_toggle_close, name='job_toggle_close'),

    # ─── RESUMELAR ───
    path('resumes/', views.resume_list, name='resume_list'),
    path('resumes/create/', views.resume_create, name='resume_create'),
    path('resumes/<uuid:pk>/', views.resume_detail, name='resume_detail'),
    path('resumes/<uuid:pk>/edit/', views.resume_edit, name='resume_edit'),
    path('resumes/<uuid:pk>/delete/', views.resume_delete, name='resume_delete'),
    path('resumes/<uuid:pk>/hired/', views.resume_toggle_hired, name='resume_toggle_hired'),

    # ─── KOMMUNAL TO'LOVLAR ───
    path('utilities/', views.utility_list, name='utility_list'),
    path('utilities/add/', views.utility_create, name='utility_create'),
    path('utilities/<uuid:pk>/edit/', views.utility_edit, name='utility_edit'),
    path('utilities/<uuid:pk>/delete/', views.utility_delete, name='utility_delete'),

    # ─── BOOST ───
    path('ads/<uuid:pk>/boost/', views.boost_ad_view, name='boost_ad'),

    # ─── ESKI URL ALIAS lar (template lar uchun) ───
    path('chat/', views.neighborhood_chat, name='neighborhood_chat_alias'),
    path('chat/<int:room_id>/', views.neighborhood_chat_room, name='neighborhood_chat_room_alias'),

    # ─── ALIAS: eski hard-coded URL lar uchun ───
    path('my-bookings/', views.my_bookings, name='my_bookings_alias'),
    path('jobs/new/', views.job_create, name='job_new'),

    # /ads/<pk>/... → /ad/<pk>/... alias lar
    path('ads/<uuid:pk>/edit/', views.ad_edit, name='ad_edit_alias'),
    path('ads/<uuid:pk>/delete/', views.ad_delete, name='ad_delete_alias'),
    path('ads/<uuid:pk>/mark-sold/', views.ad_toggle_sold, name='ad_mark_sold'),
    path('ads/<uuid:pk>/', views.ad_detail, name='ad_detail_alias'),
]
