from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from projects.models import Project # Импортируем твою модель проектов

# (Тут твой StaticViewSitemap для главной страницы, который мы делали ранее)
class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = 'weekly'

    def items(self):
        # Используем РЕАЛЬНЫЕ имена из твоего urls.py
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
# 🔥 НОВЫЙ КЛАСС ДЛЯ ПРОЕКТОВ:
class ProjectSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8 # Чуть ниже главной, но всё равно высокий приоритет

    def items(self):
        # Отдаем Гуглу только актуальные проекты (is_archived=False)
        return Project.objects.filter(is_archived=False).order_by('-created_at')

    def lastmod(self, obj):
        # Гугл будет знать, когда ты в последний раз редактировал проект
        return obj.updated_at