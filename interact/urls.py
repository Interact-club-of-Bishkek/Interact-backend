from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from users.views import (
    VolunteerViewSet, VolunteerLoginView, VolunteerProfileView,
    VolunteerApplicationViewSet, VolunteerColumnsView, SendAcceptedVolunteersEmailsView, VolunteerBoardView
)
from directions.views import VolunteerDirectionViewSet, ProjectDirectionViewSet
from projects.views import ProjectListView, YearResultListView, ProjectArchiveListView
from teatre import views

# ------------------ Swagger ------------------
schema_view = get_schema_view(
    openapi.Info(
        title="Interact Club API",
        default_version='v1',
        description="Документация API для фронтенда",
        contact=openapi.Contact(email="admin@interact.kg"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# ------------------ Router ------------------
router = DefaultRouter()
router.register(r'volunteer', VolunteerViewSet)
router.register(r'volunteer-directions', VolunteerDirectionViewSet, basename='volunteer-directions')
router.register(r'project-directions', ProjectDirectionViewSet, basename='project-directions')
router.register(r'applications', VolunteerApplicationViewSet, basename='applications')  # <-- новый роут

# ------------------ URLS ------------------
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),

    path('', include('logs.urls')),

    # Auth
    path('api/login', VolunteerLoginView.as_view(), name='volunteer-login'),
    path('api/profile', VolunteerProfileView.as_view()),

    # Volunteer columns view (для фронта)
    path('api/volunteer-columns/', VolunteerColumnsView.as_view(), name='volunteer-columns'),

    # Booking
    path('book/', views.booking_page, name='booking_page'), 
    path('api/book', views.api_book, name='api_book'),

    # Projects
    path('api/projects', ProjectListView.as_view()),
    path('api/projects/archive', ProjectArchiveListView.as_view(), name='projects-archive'),
    path('api/year-result', YearResultListView.as_view()),

    # Finik payments
    path('finik/', include('finik.urls')),

    path('users/send-accepted-emails/', SendAcceptedVolunteersEmailsView.as_view(), name='send-accepted-emails'),
    path('volunteers-board/', VolunteerBoardView.as_view(), name='volunteers-board'),


    # ------------------ Swagger ------------------
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) \
  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
