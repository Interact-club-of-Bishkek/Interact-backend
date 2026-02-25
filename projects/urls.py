from django.urls import path
from . import views
from .views import (
    HeroSlideListView,
    ProjectListView, 
    RecentProjectListView, 
    ProjectDetailView, 
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
    # --- Страницы (Frontend) ---
    path('', main_page, name='main'),
    path('promotion/', promotion_page, name='promotion'), # Добавил /
    path('project-details', project_details_page, name='project-details-html'),
    path('projects', projects_list_page, name='projects-list-html'),
    
    # --- API Endpoints (Исправлено: добавлены слеши) ---
    
    # 1. Слайды (была ошибка 404)
    path('api/hero-slides/', HeroSlideListView.as_view(), name='hero-slides'),
    path('api/partners/', views.PartnerListView.as_view(), name='api-partners'),
    # 2. Члены команды
    path('api/team-members/', TeamMemberListView.as_view(), name='team-members'),
    
    # 3. FAQ
    path('api/faqs/', FAQListView.as_view(), name='faqs'),
    
    path('donate/', donate_page, name='donate-html'),
    path('about/', about_page, name='about-html'),
    path('sponsorship/', sponsorship_page, name='sponsorship-html'),
    path('volunteer/', volunteer_page, name='volunteer-html'),
    path('privacy-policy/', privacy_page, name='privacy-html'),
    # path('test/', test_page, name='test-html'),
    path('terms-of-use/', terms_page, name='terms-html'),

    # 2. Последние проекты (была ошибка 404)
    path('api/projects/recent/', RecentProjectListView.as_view(), name='projects-recent'),
    
    # 3. Общий список проектов
    path('api/projects/', ProjectListView.as_view(), name='project-list'),
    
    # 4. Детали проекта
    path('api/projects/<int:id>/', ProjectDetailView.as_view(), name='project-detail'),
    
    # 5. Создание и архив
    path('api/projects/create/', ProjectCreateAPIView.as_view(), name='project-create'),
    path('api/projects/archive/', ProjectArchiveListView.as_view(), name='projects-archive'),
    
    # 6. Результаты года (была ошибка 404)
    # ВАЖНО: В JS мы запрашивали 'year-results/' (множественное число). 
    # Если в модели YearResult, лучше оставить путь 'api/year-results/'
    path('api/year-results/', YearResultListView.as_view(), name='year-result'),
]