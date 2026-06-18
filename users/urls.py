from django.urls import path, include
from rest_framework.routers import DefaultRouter
from users.views import (
    DeductPointsView, RemoveVolunteerFromCommandView, VolunteerLoginView, VolunteerRegisterView, VolunteerProfileView,
    VolunteerActivityViewSet, DiscoveryListView, CuratorSubmissionViewSet,
    VolunteerApplicationViewSet, VolunteerViewSet, VolunteerColumnsView,
    DownloadInterviewScheduleView, DownloadAcceptedNamesView,
    CuratorPanelView, VolunteerCabinetView, LoginPageView, VolunteerBoardView,
    VolunteerListView,
    AttendanceViewSet,  # API для отметок
    BailiffPanelView,    # HTML страница
    EquityViewSet, 
    EquityPanelView,
    get_app_settings,
    # --- НОВЫЕ ИМПОРТЫ ДЛЯ ПРИСТАВА БАЗ ---
    BailiffBasePanelView,
    generate_auto_distribution,
    apply_distribution,
    volunteer_direction_preferences,
    ai_pdf_chat,
    # --- НОВОЕ ДЛЯ МИНИ-КОМАНД И СПОНСОРОВ ---
    MiniTeamViewSet,
    SponsorTaskViewSet
)

router = DefaultRouter()

# Роутер генерирует ссылки:
# /api/volunteers/
# /api/applications/
# /api/activities/
# /api/curator/submissions/
# /api/attendance/  
# /api/equity/
router.register(r'volunteers', VolunteerViewSet, basename='volunteer')
router.register(r'applications', VolunteerApplicationViewSet, basename='application')
router.register(r'activities', VolunteerActivityViewSet, basename='vol-activity')
router.register(r'curator/submissions', CuratorSubmissionViewSet, basename='cur-submission')
router.register(r'attendance', AttendanceViewSet, basename='attendance')
router.register(r'equity', EquityViewSet, basename='equity')

# --- НОВОЕ ДЛЯ МИНИ-КОМАНД И СПОНСОРОВ ---
router.register(r'miniteams', MiniTeamViewSet, basename='miniteam')
router.register(r'sponsors', SponsorTaskViewSet, basename='sponsor')


urlpatterns = [
    # --- API Эндпоинты ---
    path('api/login/', VolunteerLoginView.as_view(), name='login'),
    path('api/register/', VolunteerRegisterView.as_view(), name='register'),
    path('api/profile/', VolunteerProfileView.as_view(), name='profile'),
    path('api/discovery/', DiscoveryListView.as_view(), name='discovery'),
    
    path('api/list/', VolunteerListView.as_view(), name='volunteer-list'),

    # Канбан-доска
    path('api/board-columns/', VolunteerColumnsView.as_view(), name='columns-list'),
    path('api/columns/', VolunteerColumnsView.as_view(), name='columns'),
    
    # --- PDF Генерация ---
    path('api/download/interviews/', DownloadInterviewScheduleView.as_view(), name='download-interviews'),
    path('api/download/accepted/', DownloadAcceptedNamesView.as_view(), name='download-accepted'),
    
    # --- НОВЫЕ API ДЛЯ РАСПРЕДЕЛЕНИЯ (Пристав Баз) ---
    path('api/generate_distribution/', generate_auto_distribution, name='generate_distribution'),
    path('api/apply_distribution/', apply_distribution, name='apply_distribution'),
    
    # Эндпоинт для отправки 3-х желаемых направлений (чтобы не конфликтовал с router.applications)
    path('api/preferences/', volunteer_direction_preferences, name='direction_preferences'),

    # --- Подключение Роутера ---
    path('api/', include(router.urls)),
    path('api/settings/', get_app_settings, name='api_settings'),
    # --- HTML Страницы ---
    path('login/', LoginPageView.as_view(), name='login-page'),
    path('cabinet/', VolunteerCabinetView.as_view(), name='cabinet'),
    path('curator-panel/', CuratorPanelView.as_view(), name='curator-panel'),
    path('board/', VolunteerBoardView.as_view(), name='board'),
    path('commands/<int:pk>/remove-volunteer/', RemoveVolunteerFromCommandView.as_view(), name='remove-volunteer'),
    path('api/curator/penalty/', DeductPointsView.as_view(), name='deduct-points'),
    
    # Панели
    path('bailiff-panel/', BailiffPanelView.as_view(), name='bailiff-panel'),
    path('equity-panel/', EquityPanelView.as_view(), name='equity_panel'),
    
    # --- НОВАЯ СТРАНИЦА ПРИСТАВА БАЗ ---
    path('bailiff-base-panel/', BailiffBasePanelView.as_view(), name='bailiff_base_panel'),

    path('api/chat/', ai_pdf_chat, name='ai_pdf_chat'),
]