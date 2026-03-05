from django.urls import path
from . import views
from .views import (
    HeroSlideListView,
    # ProjectListView, # Если тебе нужен API список всех проектов (JSON), раскомментируй эту вьюху во views.py
    RecentProjectListView, 
    # ProjectDetailView, 
    ProjectCreateAPIView, 
    ProjectArchiveListView, 
    YearResultListView,
    donate_page, 
    about_page,
    main_page,
    privacy_page,
    promotion_page,
    project_details_page,
    projects_list_page,
    TeamMemberListView,
    FAQListView,
    sponsorship_page,
    terms_page,
    # test_page,
    volunteer_page
)

urlpatterns = [
    # --- Страницы (Frontend / HTML) ---
    path('', main_page, name='main'),
    path('promotion/', promotion_page, name='promotion'),
    
    # ИСПРАВЛЕНО: Удалили старый дубль 'project-details' без слага.
    # Оставили только правильные пути для каталога и детальной страницы:
    path('projects/', projects_list_page, name='projects-list-html'),
    path('projects/<slug:slug>/', project_details_page, name='project-details-html'), 
    
    path('donate/', donate_page, name='donate-html'),
    path('about/', about_page, name='about-html'),
    path('sponsorship/', sponsorship_page, name='sponsorship-html'),
    path('volunteer/', volunteer_page, name='volunteer-html'),
    path('privacy-policy/', privacy_page, name='privacy-html'),
    path('terms-of-use/', terms_page, name='terms-html'),
    # path('test/', test_page, name='test-html'),

    # --- API Endpoints (Возвращают JSON для JavaScript) ---
    
    # 1. Слайды и Партнеры
    path('api/hero-slides/', HeroSlideListView.as_view(), name='hero-slides'),
    path('api/partners/', views.PartnerListView.as_view(), name='api-partners'),
    
    # 2. Члены команды и FAQ
    path('api/team-members/', TeamMemberListView.as_view(), name='team-members'),
    path('api/faqs/', FAQListView.as_view(), name='faqs'),
    
    # 3. Проекты (API)
    path('api/projects/recent/', RecentProjectListView.as_view(), name='projects-recent'),
    
    # ИСПРАВЛЕНО: Раньше здесь стоял views.projects_list_page (который возвращает HTML).
    # Если на главной странице (или где-то еще) JS делает fetch('/api/projects/'), 
    # тебе нужно вернуть сюда ProjectListView.as_view()!
    # Если этот путь больше нигде не запрашивается из JS, его можно просто закомментировать.
    path('api/projects/', views.projects_list_page, name='projects-list-html'),

    path('api/projects/create/', ProjectCreateAPIView.as_view(), name='project-create'),
    path('api/projects/archive/', ProjectArchiveListView.as_view(), name='projects-archive'),
    
    # 4. Результаты года
    path('api/year-results/', YearResultListView.as_view(), name='year-result'),
]