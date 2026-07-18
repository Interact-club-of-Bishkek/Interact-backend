from django.urls import path
from .views import (
    CommandListView, 
    CommandDetailView, 
    ApplicationListCreateView, 
    ApplicationUpdateStatusView, 
    AddVolunteerToCommandView,
    RemoveVolunteerFromCommandView,
    curator_page, 
    volunteer_page,
    president_page  # 🔥 ИМПОРТИРУЕМ НОВУЮ ФУНКЦИЮ
)

urlpatterns = [
    # --- Страницы (Шаблоны) ---
    path('join-commands', volunteer_page, name='volunteer-page'),
    # path('dashboard-teamliders', curator_page, name='curator-page'),
    
    # 🔥 ИЗМЕНЕННЫЙ ПУТЬ ДЛЯ ПРЕЗИДЕНТА
    path('president-panel/', president_page, name='president-panel'),
    
    # --- API Команд ---
    path('commands/', CommandListView.as_view(), name='command-list'),
    path('commands/<str:slug>/', CommandDetailView.as_view(), name='command-detail'),
    
    # --- API Заявок ---
    path('commands-applications/', ApplicationListCreateView.as_view(), name='app-list-create'),
    path('commands-applications/<int:pk>/accept/', ApplicationUpdateStatusView.as_view(), name='app-accept'),
    
    # --- API Управления составом (строго с префиксом commands/ для фронтенда) ---
    path('commands/<int:pk>/add-volunteer/', AddVolunteerToCommandView.as_view(), name='add_volunteer'),
    path('commands/<int:pk>/remove-volunteer/', RemoveVolunteerFromCommandView.as_view(), name='remove_volunteer'),
]