from django.urls import path
from .views import (
    CommandListView, CommandDetailView, 
    ApplicationListCreateView, ApplicationUpdateStatusView, curator_page, volunteer_page
)

urlpatterns = [
    path('join-commands', volunteer_page, name='volunteer-page'),
    path('dashboard-teamliders', curator_page, name='curator-page'),

    path('commands/', CommandListView.as_view(), name='command-list'),
    path('commands/<str:slug>/', CommandDetailView.as_view(), name='command-detail'),
    path('commands-applications/', ApplicationListCreateView.as_view(), name='app-list-create'),
    path('commands-applications/<int:pk>/accept/', ApplicationUpdateStatusView.as_view(), name='app-accept'),
]