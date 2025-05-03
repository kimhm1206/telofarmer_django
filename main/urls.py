from django.urls import path
from . import views

urlpatterns = [
    path('settings/', views.setting_view, name='setting_view'),
    path('settings/update/', views.update_setting, name='update_setting'),
    path('settings/overwrite/', views.overwrite_setting, name='overwrite_setting'),
    path('settings/download/', views.download_setting, name='download_setting'),
    
    path('', views.login_page, name='login_page'),
    path('login/', views.login_process, name='login_process'),

    # 추가된 뷰 경로들
    path('dashboard/', views.dashboard_view, name='dashboard_view'),
    path('data/', views.data_view, name='data_view'),
    path('log/', views.log_view, name='log_view'),
    path("log/refresh/",views.log_refresh, name="log_refresh"),
    path("log/download/<int:channel>/", views.download_log),
    path("api/logdata/", views.api_logdata, name="api_logdata"),
    path("api/testdata/", views.api_testdata, name="api_testdata"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("system_update/", views.system_update, name="system_update"),
]