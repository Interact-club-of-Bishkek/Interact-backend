from django.contrib import admin
from django.db import models
from django.db.models import Q
from .models import (
    Volunteer, VolunteerApplication, VolunteerArchive, 
    ActivityTask, ActivitySubmission, BotAccessConfig
)

# Inline для просмотра заданий внутри профиля волонтера
class ActivitySubmissionInline(admin.TabularInline):
    model = ActivitySubmission
    extra = 0
    verbose_name = "Выполненное задание"
    verbose_name_plural = "История заданий"
    readonly_fields = ('created_at',)
    fields = ('task', 'status', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj):
        return False

@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('name', 'login', 'role', 'point', 'yellow_card', 'is_active')
    list_filter = ('role', 'is_active', 'direction', 'commands')
    search_fields = ('name', 'login', 'phone_number')
    readonly_fields = ('login', 'visible_password') # point можно редактировать админу
    filter_horizontal = ('direction', 'commands') 
    inlines = [ActivitySubmissionInline]
    
    fieldsets = (
        ('Учетные данные', {
            'fields': ('login', 'visible_password', 'role', 'is_active')
        }),
        ('Личные данные', {
            'fields': ('name', 'phone_number', 'email', 'image')
        }),
        ('Структура', {
            'fields': ('direction', 'commands')
        }),
        ('Статистика', {
            'fields': ('point', 'yellow_card')
        }),
    )

@admin.register(VolunteerApplication)
class VolunteerApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'direction_name', 'status', 'phone_number', 'created_at')
    list_filter = ('status', 'direction')
    search_fields = ('full_name', 'phone_number')
    filter_horizontal = ('commands',)

    def direction_name(self, obj):
        return obj.direction.name if obj.direction else "-"
    direction_name.short_description = "Направление"

@admin.register(ActivityTask)
class ActivityTaskAdmin(admin.ModelAdmin):
    # ИСПРАВЛЕНИЕ: Убрали direction, так как его нет в модели
    list_display = ('title', 'points', 'get_visibility')
    list_filter = ('command',) 
    search_fields = ('title',)

    # Кастомная колонка для удобства
    def get_visibility(self, obj):
        if obj.command:
            return f"🔒 Только команда: {obj.command.title}"
        return "🌍 ОБЩЕЕ (Видно всем)"
    get_visibility.short_description = "Видимость"

@admin.register(ActivitySubmission)
class ActivitySubmissionAdmin(admin.ModelAdmin):
    list_display = ('volunteer', 'task', 'status', 'created_at')
    # ИСПРАВЛЕНИЕ: Фильтруем по статусу и команде задачи (direction у задачи нет)
    list_filter = ('status', 'task__command')
    search_fields = ('volunteer__name', 'task__title')
    actions = ['approve_selected', 'reject_selected']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.role == 'admin':
            return qs
        
        # ЛОГИКА ВИДИМОСТИ ДЛЯ КУРАТОРА:
        # 1. Куратор видит задачи, привязанные к ЕГО команде (где он лидер).
        # 2. Куратор видит задачи, выполненные волонтерами ИЗ ЕГО направления (даже если задача общая).
        return qs.filter(
            Q(task__command__leader=request.user) | 
            Q(volunteer__direction__responsible=request.user)
        ).distinct()

    @admin.action(description="✅ Одобрить и начислить баллы")
    def approve_selected(self, request, queryset):
        for obj in queryset.filter(status='pending'):
            obj.status = 'approved'
            obj.save() # Вызовет метод save() модели и начислит баллы

    @admin.action(description="❌ Отклонить выбранные")
    def reject_selected(self, request, queryset):
        # Тут используем цикл, чтобы сработал save() и снялись баллы (если вдруг они были начислены)
        # Или просто update, если мы уверены, что снимать не надо.
        # Для безопасности лучше через цикл, если логика сложная:
        for obj in queryset.filter(status='pending'):
            obj.status = 'rejected'
            obj.save()

admin.site.register(BotAccessConfig)
admin.site.register(VolunteerArchive)
