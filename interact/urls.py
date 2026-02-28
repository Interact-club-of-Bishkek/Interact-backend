# urls.py (ГЛАВНЫЙ)
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static

from rest_framework.routers import DefaultRouter
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.contrib.sitemaps.views import sitemap
from .sitemaps import ProjectSitemap, StaticViewSitemap # Импортируем наш класс из файла sitemaps.py
# Импорты только для роутера
from users.views import VolunteerViewSet, VolunteerApplicationViewSet
from directions.views import VolunteerDirectionViewSet, ProjectDirectionViewSet

# ------------------ Swagger Setup ------------------
schema_view = get_schema_view(
    openapi.Info(
        title="Interact Club API",
        default_version='v1',
        description="Документация API для фронтенда",
        contact=openapi.Contact(email="admin@interact.kg"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# ------------------ Router Setup ------------------
# ViewSets остаются здесь, так как они формируют REST структуру
router = DefaultRouter()
router.register(r'volunteer', VolunteerViewSet)
router.register(r'volunteer-directions', VolunteerDirectionViewSet, basename='volunteer-directions')
router.register(r'project-directions', ProjectDirectionViewSet, basename='project-directions')
router.register(r'applications', VolunteerApplicationViewSet, basename='applications')

sitemaps = {
    'static': StaticViewSitemap,
    'projects': ProjectSitemap, # Подключили проекты
}

# ------------------ Main URL Patterns ------------------
urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Подключаем роутер (ViewSet'ы)
    path('api/', include(router.urls)),

    # Подключаем urls из приложений (APIViews и обычные Views)
    path('', include('users.urls')),      # Auth, Profile, Board, Bot
    path('', include('projects.urls')),   # Main page, Projects API
    path('', include('teatre.urls')),     # Booking
    path('', include('logs.urls')),       # Logs
    path('', include('commands.urls')),       # Logs

    path('finik/', include('finik.urls')), # Payments

    # ------------------ Swagger ------------------
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),


    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) \
  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'projects.views.custom_page_not_found'