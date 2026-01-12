# teatre/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('book/', views.booking_page, name='booking_page'), 
    path('api/book', views.api_book, name='api_book'),
]