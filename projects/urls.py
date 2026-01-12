# projects/urls.py
from django.urls import path
from .views import (
    ProjectListView, 
    ProjectCreateAPIView, 
    ProjectArchiveListView, 
    YearResultListView, 
    main_page
)

urlpatterns = [
    # Main Page
    path('', main_page, name='main'),

    # Projects API
    path('api/projects', ProjectListView.as_view(), name='project-list'),
    path('api/projects/create', ProjectCreateAPIView.as_view(), name='project-create'),
    path('api/projects/archive', ProjectArchiveListView.as_view(), name='projects-archive'),
    path('api/year-result', YearResultListView.as_view(), name='year-result'),
]