from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VolunteerLoginView, VolunteerRegisterView, VolunteerProfileView,
    VolunteerActivityViewSet, DiscoveryListView, CuratorSubmissionViewSet,
    VolunteerApplicationViewSet, VolunteerViewSet, VolunteerColumnsView,
    DownloadInterviewScheduleView, DownloadAcceptedNamesView,
    CuratorPanelView, VolunteerCabinetView, LoginPageView, VolunteerBoardView,
    VolunteerListView,
    # --- НОВЫЕ ИМПОРТЫ ---
    AttendanceViewSet,  # API для отметок
    BailiffPanelView,    # HTML страница
    EquityViewSet, 
    EquityPanelView
)

router = DefaultRouter()

# Роутер генерирует ссылки:
# /api/volunteers/
# /api/applications/
# /api/activities/
# /api/curator/submissions/
# /api/attendance/  <-- НОВОЕ
router.register(r'volunteers', VolunteerViewSet, basename='volunteer')
router.register(r'applications', VolunteerApplicationViewSet, basename='application')
router.register(r'activities', VolunteerActivityViewSet, basename='vol-activity')
router.register(r'curator/submissions', CuratorSubmissionViewSet, basename='cur-submission')
# Регистрация API посещаемости
router.register(r'attendance', AttendanceViewSet, basename='attendance')
router.register(r'equity', EquityViewSet, basename='equity')
urlpatterns = [
    # --- API Эндпоинты ---
    path('api/login/', VolunteerLoginView.as_view(), name='login'),
    path('api/register/', VolunteerRegisterView.as_view(), name='register'),
    path('api/profile/', VolunteerProfileView.as_view(), name='profile'),
    path('api/discovery/', DiscoveryListView.as_view(), name='discovery'),
    
    path('api/list/', VolunteerListView.as_view(), name='volunteer-list'),

    # 2. Канбан-доска
    path('api/board-columns/', VolunteerColumnsView.as_view(), name='columns-list'),
    path('api/columns/', VolunteerColumnsView.as_view(), name='columns'),
    
    # --- PDF Генерация ---
    path('api/download/interviews/', DownloadInterviewScheduleView.as_view(), name='download-interviews'),
    path('api/download/accepted/', DownloadAcceptedNamesView.as_view(), name='download-accepted'),
    
    # --- Подключение Роутера ---
    path('api/', include(router.urls)),

    # --- HTML Страницы ---
    path('login/', LoginPageView.as_view(), name='login-page'),
    path('cabinet/', VolunteerCabinetView.as_view(), name='cabinet'),
    path('curator-panel/', CuratorPanelView.as_view(), name='curator-panel'),
    path('board/', VolunteerBoardView.as_view(), name='board'),
    
    # НОВЫЙ ПУТЬ ДЛЯ ПРИСТАВА
    path('bailiff-panel/', BailiffPanelView.as_view(), name='bailiff-panel'),
    path('equity-panel/', EquityPanelView.as_view(), name='equity_panel'),
]