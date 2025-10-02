from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from users.views import DirectionViewSet, VolunteerViewSet, VolunteerLoginView, VolunteerProfileView
from form.views import (
    VolunteerFormListView, VolunteerFormDetailView,
    WaitingListListView, WaitingListDetailView,
    MailingPendingListView, MailingPendingDetailView,
    VerifyVolunteerFormView, ApproveWaitingListView, ApproveAllFromMailingPendingView,
    SendTextToWaitingListView, schedule_view
)

from teatre import views


router = DefaultRouter()
router.register(r'direction', DirectionViewSet)
router.register(r'volunteer', VolunteerViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),

    path('api/login', VolunteerLoginView.as_view(), name='volunteer-login'),
    path('api/profile', VolunteerProfileView.as_view()),

    path('api/volunteerform', VolunteerFormListView.as_view()),
    path('api/volunteerform/<int:pk>', VolunteerFormDetailView.as_view()),
    path('api/volunteerform/<int:pk>/verify', VerifyVolunteerFormView.as_view()),

    path('api/waitinglist', WaitingListListView.as_view()),
    path('api/waitinglist/<int:pk>', WaitingListDetailView.as_view()),
    path('api/waitinglist/<int:pk>/approve', ApproveWaitingListView.as_view()),

    path('api/mailingpending', MailingPendingListView.as_view()),
    path('api/mailingpending/<int:pk>', MailingPendingDetailView.as_view()),

    path('mailing/approve-all', ApproveAllFromMailingPendingView.as_view()),

    path("waitinglist/send-text", SendTextToWaitingListView.as_view()),

    path('schedule', schedule_view, name='schedule'),

    path('book/', views.booking_page, name='booking_page'), 
    path('api/book/', views.api_book, name='api_book'),

    path('finik/', include('finik.urls')),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)