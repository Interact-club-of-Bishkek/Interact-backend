from django.urls import path
from .views import (
    # Страницы
    volunteer_page,
    curator_page,
    president_page,
    board_page,

    # API Команд
    CommandListView, 
    CommandDetailView, 
    ApplicationListCreateView,  
    ApplicationUpdateStatusView, 
    AddVolunteerToCommandView,
    RemoveVolunteerFromCommandView,
    
    # API Борда
    BoardPositionListView,
    BoardPositionDetailView,
    BoardApplicationListCreateView,
    BoardApplicationUpdateStatusView,
    AddVolunteerToBoardView,
    RemoveVolunteerFromBoardView
)

urlpatterns = [
    # ==========================================
    # Страницы (Шаблоны)
    # ==========================================
    path('join-commands/', volunteer_page, name='volunteer-page'),
    path('join-board/', board_page, name='board-page'),
    path('president-panel/', president_page, name='president-panel'),
    # path('dashboard-teamliders/', curator_page, name='curator-page'),
    
    # ==========================================
    # API Команд
    # ==========================================
    path('commands/', CommandListView.as_view(), name='command-list'),
    path('commands/<str:slug>/', CommandDetailView.as_view(), name='command-detail'),
    path('commands-applications/', ApplicationListCreateView.as_view(), name='app-list-create'),
    path('commands-applications/<int:pk>/accept/', ApplicationUpdateStatusView.as_view(), name='app-accept'),
    path('commands/<int:pk>/add-volunteer/', AddVolunteerToCommandView.as_view(), name='add_volunteer'),
    path('commands/<int:pk>/remove-volunteer/', RemoveVolunteerFromCommandView.as_view(), name='remove_volunteer'),

    # ==========================================
    # API Борда
    # ==========================================
    path(
        'board/',
        BoardPositionListView.as_view(),
        name='board-list'
    ),    
    path('board/<str:slug>/', BoardPositionDetailView.as_view(), name='board-detail'),
    path('board-applications/', BoardApplicationListCreateView.as_view(), name='board-app-list-create'),
    path('board-applications/<int:pk>/accept/', BoardApplicationUpdateStatusView.as_view(), name='board-app-accept'),
    path('board/<int:pk>/add-member/', AddVolunteerToBoardView.as_view(), name='board-add-member'),
    path('board/<int:pk>/remove-member/', RemoveVolunteerFromBoardView.as_view(), name='board-remove-member'),
]