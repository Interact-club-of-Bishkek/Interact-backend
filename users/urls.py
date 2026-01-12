# users/urls.py
from django.urls import path
from .views import (
    VolunteerLoginView, 
    VolunteerProfileView, 
    VolunteerColumnsView, 
    SendAcceptedVolunteersEmailsView, 
    VolunteerBoardView, 
    BotCheckAccessView
)

urlpatterns = [
    # Auth
    path('api/login', VolunteerLoginView.as_view(), name='volunteer-login'),
    path('api/profile', VolunteerProfileView.as_view(), name='volunteer-profile'),

    # Volunteer columns view
    path('api/volunteer-columns/', VolunteerColumnsView.as_view(), name='volunteer-columns'),

    # Emails & Board
    path('users/send-accepted-emails/', SendAcceptedVolunteersEmailsView.as_view(), name='send-accepted-emails'),
    path('volunteers-board/', VolunteerBoardView.as_view(), name='volunteers-board'),

    # Bot
    path('api/bot-auth/', BotCheckAccessView.as_view(), name='bot_auth'),
]