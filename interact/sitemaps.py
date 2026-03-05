from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from projects.models import Project # Убедись, что импорт правильный (точка означает текущую папку)

class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = 'weekly'

    def items(self):
        return [
            'main', 
            'about-html', 
            'donate-html', 
            'volunteer-html', 
            'sponsorship-html', 
            'projects-list-html'
        ]

    def location(self, item):
        return reverse(item)

# 🔥 КЛАСС ДЛЯ ПРОЕКТОВ:
class ProjectSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        # Отдаем Гуглу только актуальные проекты
        return Project.objects.filter(is_archived=False).order_by('-created_at')

    def lastmod(self, obj):
        return obj.updated_at
        
    # ДОБАВЛЯЕМ ЭТОТ МЕТОД:
    def location(self, obj):
        # Берем имя пути из твоего urls.py и передаем slug проекта
        return reverse('project-details-html', kwargs={'slug': obj.slug})