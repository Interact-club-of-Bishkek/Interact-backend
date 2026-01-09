# directions/admin.py
from django.contrib import admin
from directions.models import VolunteerDirection, ProjectDirection

@admin.register(VolunteerDirection)
class VolunteerDirectionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "volunteers_count")
    search_fields = ("name",)

    def volunteers_count(self, obj):
        return obj.volunteers.count()
    volunteers_count.short_description = "Количество волонтёров"


@admin.register(ProjectDirection)
class ProjectDirectionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "projects_count")
    search_fields = ("name",)

    def projects_count(self, obj):
        return obj.projects.count()
    projects_count.short_description = "Количество проектов"


