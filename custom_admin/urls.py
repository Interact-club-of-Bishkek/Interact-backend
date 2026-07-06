from django.urls import path
from .views import (
    AdminDashboardView,
    toggle_settings,
    handle_application,
    handle_submission,
    update_volunteer_points,
)

urlpatterns = [
    # --- Главная страница кастомной админки ---
    path('custom-admin/', AdminDashboardView.as_view(), name='custom_admin'),
    
    # --- AJAX API (работа кнопок и тумблеров без перезагрузки страницы) ---
    path('api/toggle-settings/', toggle_settings, name='toggle_settings'),
    path('api/handle-application/', handle_application, name='handle_application'),
    path('api/handle-submission/', handle_submission, name='handle_submission'),
    path('api/update-points/', update_volunteer_points, name='update_points'),
]