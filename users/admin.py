from django.contrib import admin
from django.db import models
from .models import (
    Volunteer, VolunteerApplication, VolunteerArchive, 
    ActivityTask, ActivitySubmission, BotAccessConfig
)
# Направления и Команды НЕ импортируем здесь, если они зарегистрированы в своих приложениях

class ActivitySubmissionInline(admin.TabularInline):
    model = ActivitySubmission
    extra = 0
    verbose_name = "Выполненное задание"
    verbose_name_plural = "История заданий"
    readonly_fields = ('created_at',)
    fields = ('task', 'status', 'created_at')

@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('name', 'login', 'role', 'point', 'is_active')
    list_filter = ('role', 'is_active', 'direction', 'commands')
    search_fields = ('name', 'login', 'phone_number')
    readonly_fields = ('login', 'visible_password', 'point')
    filter_horizontal = ('direction', 'commands') 
    inlines = [ActivitySubmissionInline]

@admin.register(VolunteerApplication)
class VolunteerApplicationAdmin(admin.ModelAdmin):
    # Тут используем 'direction' (новое поле)
    list_display = ('full_name', 'direction', 'status', 'phone_number', 'created_at')
    list_filter = ('status', 'direction')
    search_fields = ('full_name', 'phone_number')
    filter_horizontal = ('commands',)

@admin.register(ActivityTask)
class ActivityTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'points', 'direction', 'command')
    list_filter = ('direction', 'command')
    search_fields = ('title',)

@admin.register(ActivitySubmission)
class ActivitySubmissionAdmin(admin.ModelAdmin):
    list_display = ('volunteer', 'task', 'status', 'created_at')
    list_filter = ('status', 'task__direction', 'task__command')
    search_fields = ('volunteer__name', 'task__title')
    actions = ['approve_selected', 'reject_selected']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.role == 'admin':
            return qs
        from django.db.models import Q
        return qs.filter(
            Q(task__direction__responsible=request.user) | 
            Q(task__command__leader=request.user)
        ).distinct()

    @admin.action(description="✅ Одобрить и начислить баллы")
    def approve_selected(self, request, queryset):
        for obj in queryset.filter(status='pending'):
            obj.status = 'approved'
            obj.save()

    @admin.action(description="❌ Отклонить выбранные")
    def reject_selected(self, request, queryset):
        queryset.filter(status='pending').update(status='rejected')

admin.site.register(BotAccessConfig)
admin.site.register(VolunteerArchive)