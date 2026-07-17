from django.urls import path
from django.contrib.auth.views import LogoutView
from django.views.generic import RedirectView
from . import views
from . import community_views
from . import marketplace_views

class LogoutGetView(LogoutView):
    """Logout'ni GET (havola) yoki POST orqali bajaradi.

    Django 5.x'da LogoutView faqat POST'da chiqaradi — GET esa TemplateView'dan
    meros olingan get() tufayli sessiyani tozalamasdan "chiqdingiz" sahifasini
    ko'rsatadi (foydalanuvchi tizimda qolib ketadi). get() ni post() ga
    yo'naltirib, havola orqali chiqishni ham haqiqiy ishlaydigan qilamiz.
    """
    http_method_names = ['get', 'post', 'options']

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

urlpatterns = [
    # Asosiy
    path('', views.home, name='home'),
    path('app/', views.app_download, name='app_download'),
    path('download/samcity.apk', views.download_apk, name='download_apk'),
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
    path('ad/<uuid:pk>/', views.ad_detail, name='ad_detail'),
    path('ad/<uuid:pk>/edit/', views.ad_edit, name='ad_edit'),
    path('ad/<uuid:pk>/delete/', views.ad_delete, name='ad_delete'),
    path('ad/<uuid:pk>/toggle-sold/', views.ad_toggle_sold, name='ad_toggle_sold'),

    # ─── GLOBAL SEARCH ──────────────────────────────────────────────────────
    path('search/', marketplace_views.global_search, name='global_search'),
    path('search/autocomplete/', marketplace_views.search_autocomplete, name='search_autocomplete'),

    # ─── MARKETPLACE (ad favorites / report / inquiry) ──────────────────────
    path('ads/saved/', marketplace_views.saved_ads, name='saved_ads'),
    path('ads/<uuid:pk>/favorite/', marketplace_views.ad_favorite_toggle, name='ad_favorite'),
    path('ads/<uuid:pk>/report/', marketplace_views.ad_report, name='ad_report'),
    path('ads/<uuid:pk>/inquiry/', marketplace_views.ad_inquiry, name='ad_inquiry'),

    # ─── COMMUNITY: POLLS ───────────────────────────────────────────────────
    path('community/polls/', community_views.poll_list, name='poll_list'),
    path('community/polls/create/', community_views.poll_create, name='poll_create'),
    path('community/polls/<uuid:poll_id>/', community_views.poll_detail, name='poll_detail'),
    path('community/polls/<uuid:poll_id>/vote/', community_views.poll_vote, name='poll_vote'),
    path('community/polls/<uuid:poll_id>/comment/', community_views.poll_comment, name='poll_comment'),

    # ─── MAHALLA sahifasi (ma'lumot, e'lonlar, joylar, xarita, chat, murojaat) ─
    path('mahalla/', community_views.mahalla_home, name='mahalla_home'),
    path('mahalla/<int:pk>/select/', community_views.mahalla_select, name='mahalla_select'),
    path('mahalla/<int:pk>/', community_views.mahalla_detail, name='mahalla_detail'),
    path('mahalla/<int:pk>/announce/', community_views.announcement_create, name='mahalla_announce'),
    path('mahalla/<int:pk>/complaint/', community_views.citizen_request_create, name='mahalla_complaint'),
    path('mahalla/complaint/<uuid:req_id>/status/', community_views.citizen_request_status, name='mahalla_complaint_status'),

    # ─── HOKIM PANELI (tuman hokimi — butun tumanga e'lon) ────────────────────
    path('hokim/', community_views.hokim_panel, name='hokim_panel'),
    path('hokim/<int:pk>/announce/', community_views.district_announce, name='district_announce'),

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

    # /ads/<pk>/ → ad_detail alias (ad_form.html dagi hard-coded "Bekor qilish" havolasi ishlatadi)
    path('ads/<uuid:pk>/', views.ad_detail, name='ad_detail_alias'),
]
