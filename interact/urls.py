from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from users.views import DirectionViewSet, VolunteerViewSet, VolunteerLoginView, VolunteerProfileView
# from form.views import (
#     VolunteerFormListView, VolunteerFormDetailView,
#     WaitingListListView, WaitingListDetailView,
#     MailingPendingListView, MailingPendingDetailView,
#     VerifyVolunteerFormView, ApproveWaitingListView, ApproveAllFromMailingPendingView,
#     SendTextToWaitingListView, schedule_view
# )
from teatre import views
from projects.views import ProjectListView, YearResultListView

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
router.register(r'direction', DirectionViewSet)
router.register(r'volunteer', VolunteerViewSet)

# ------------------ URLS ------------------
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),

    # Auth
    path('api/login', VolunteerLoginView.as_view(), name='volunteer-login'),
    path('api/profile', VolunteerProfileView.as_view()),

    # # Volunteer Forms
    # path('api/volunteerform', VolunteerFormListView.as_view()),
    # path('api/volunteerform/<int:pk>', VolunteerFormDetailView.as_view()),
    # path('api/volunteerform/<int:pk>/verify', VerifyVolunteerFormView.as_view()),

    # # Waiting List
    # path('api/waitinglist', WaitingListListView.as_view()),
    # path('api/waitinglist/<int:pk>', WaitingListDetailView.as_view()),
    # path('api/waitinglist/<int:pk>/approve', ApproveWaitingListView.as_view()),

    # # Mailing
    # path('api/mailingpending', MailingPendingListView.as_view()),
    # path('api/mailingpending/<int:pk>', MailingPendingDetailView.as_view()),
    # path('mailing/approve-all', ApproveAllFromMailingPendingView.as_view()),

    # # Send text
    # path("waitinglist/send-text", SendTextToWaitingListView.as_view()),

    # Schedule
    # path('schedule', schedule_view, name='schedule'),

    # Booking
    path('book/', views.booking_page, name='booking_page'), 
    path('api/book', views.api_book, name='api_book'),

    # Projects
    path('api/projects', ProjectListView.as_view()),
    path('api/year-result', YearResultListView.as_view()),

    # Finik payments
    path('finik/', include('finik.urls')),

    # ------------------ Swagger ------------------
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) \
  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)