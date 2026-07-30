from django.urls import path
from .views import (
    # Страницы
    volunteer_page,

    president_page,

    # API Команд
    CommandListView, 
    CommandDetailView, 
    ApplicationListCreateView,  
    ApplicationUpdateStatusView, 
    AddVolunteerToCommandView,
    RemoveVolunteerFromCommandView,
    

)

urlpatterns = [
    # ==========================================
    # Страницы (Шаблоны)
    # ==========================================
    path('join-commands/', volunteer_page, name='volunteer-page'),
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

]