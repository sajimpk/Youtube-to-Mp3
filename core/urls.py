from django.urls import path
from core import views

app_name = 'core'

urlpatterns = [
    path('', views.index_view, name='index'),
    path('api/fetch-info/', views.api_fetch_info, name='api_fetch_info'),
    path('api/download/', views.api_start_download, name='api_start_download'),
    path('api/progress/<str:task_id>/', views.api_check_progress, name='api_check_progress'),
    path('api/get-file/<str:task_id>/', views.api_download_file, name='api_download_file'),
    path('api/history/', views.api_get_history, name='api_get_history'),
    path('api/clear-history/', views.api_clear_history, name='api_clear_history'),
]
