from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VolunteerLoginView, VolunteerRegisterView, VolunteerProfileView,
    VolunteerActivityViewSet, DiscoveryListView, CuratorSubmissionViewSet,
    VolunteerApplicationViewSet, VolunteerViewSet, VolunteerColumnsView,
    DownloadInterviewScheduleView, DownloadAcceptedNamesView,
    CuratorPanelView, VolunteerCabinetView, LoginPageView, VolunteerBoardView,
    VolunteerListView
)

router = DefaultRouter()

# Роутер генерирует ссылки:
# /api/volunteers/
# /api/applications/
# /api/activities/
# /api/curator/submissions/
router.register(r'volunteers', VolunteerViewSet, basename='volunteer')
router.register(r'applications', VolunteerApplicationViewSet, basename='application')
router.register(r'activities', VolunteerActivityViewSet, basename='vol-activity')
router.register(r'curator/submissions', CuratorSubmissionViewSet, basename='cur-submission')

urlpatterns = [
    # --- API Эндпоинты ---
    path('api/login/', VolunteerLoginView.as_view(), name='login'),
    path('api/register/', VolunteerRegisterView.as_view(), name='register'),
    path('api/profile/', VolunteerProfileView.as_view(), name='profile'),
    path('api/discovery/', DiscoveryListView.as_view(), name='discovery'),
    
    # ИСПРАВЛЕНИЕ: Добавляем api/list/, так как фронтенд ищет именно его
    path('api/list/', VolunteerListView.as_view(), name='volunteer-list'),

    # 2. Канбан-доска (переименуем, чтобы не мешала)
    path('api/board-columns/', VolunteerColumnsView.as_view(), name='columns-list'),
    # Оставляем старый путь на всякий случай
    path('api/columns/', VolunteerColumnsView.as_view(), name='columns'),
    
    # --- PDF Генерация ---
    path('api/download/interviews/', DownloadInterviewScheduleView.as_view(), name='download-interviews'),
    path('api/download/accepted/', DownloadAcceptedNamesView.as_view(), name='download-accepted'),
    
    # --- Подключение Роутера ---
    # Важно: все пути роутера будут начинаться с /api/
    path('api/', include(router.urls)),

    # --- HTML Страницы ---
    path('login/', LoginPageView.as_view(), name='login-page'), # Добавил слеш в конце для стандарта
    path('cabinet/', VolunteerCabinetView.as_view(), name='cabinet'),
    path('curator-panel/', CuratorPanelView.as_view(), name='curator-panel'),
    path('board/', VolunteerBoardView.as_view(), name='board'),
]