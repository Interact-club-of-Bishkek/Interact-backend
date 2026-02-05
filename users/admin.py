from django.contrib import admin
from django.db import models
from django.db.models import Q
from django.utils.html import format_html
from .models import (
    Volunteer, VolunteerApplication, VolunteerArchive, 
    ActivityTask, ActivitySubmission, BotAccessConfig
)

# --- INLINES ---
class ActivitySubmissionInline(admin.TabularInline):
    model = ActivitySubmission
    extra = 0
    verbose_name = "Выполненное задание"
    verbose_name_plural = "История заданий"
    readonly_fields = ('created_at',)
    fields = ('task', 'status', 'created_at')
    can_delete = False
    def has_add_permission(self, request, obj): return False

# --- VOLUNTEER ---
@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('name', 'login', 'display_password', 'role', 'point', 'is_staff', 'is_active')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'direction', 'commands')
    search_fields = ('name', 'login', 'phone_number')
    
    readonly_fields = ('login',) 
    
    # Добавляем системные поля groups и permissions для удобного выбора
    filter_horizontal = ('direction', 'commands', 'groups', 'user_permissions') 
    inlines = [ActivitySubmissionInline]
    
    fieldsets = (
        ('Учетные данные', {
            'fields': (('login', 'visible_password'), 'role')
        }),
        ('Статусы доступа', {
            'fields': (('is_active', 'is_staff', 'is_superuser'),),
            'description': '<b>is_staff</b> — дает доступ в админку. <b>is_superuser</b> — дает полные права на всё.'
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
        # Скрытый блок для детальной настройки прав (через группы)
        ('Расширенные права', {
            'fields': ('groups', 'user_permissions'),
            'classes': ('collapse',), 
        }),
    )

    def save_model(self, request, obj, form, change):
        # 1. Синхронизация пароля
        if not change or 'visible_password' in form.changed_data:
            if obj.visible_password:
                obj.set_password(obj.visible_password)
        
        # 2. Авто-назначение прав по роли
        # Если ты выбираешь роль 'admin', система сама может ставить галочку входа
        if obj.role == 'admin':
            obj.is_staff = True
            
        super().save_model(request, obj, form, change)

    def display_password(self, obj):
        if obj.visible_password:
            return format_html(
                '<code style="background: #fdf2f2; padding: 3px 6px; border-radius: 4px; color: #d63384; font-weight: bold;">{}</code>',
                obj.visible_password
            )
        return format_html('<span style="color: #999;">—</span>')
    display_password.short_description = "Пароль"

# --- APPLICATIONS ---
@admin.register(VolunteerApplication)
class VolunteerApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'direction_name', 'status', 'phone_number', 'created_at')
    list_filter = ('status', 'direction')
    search_fields = ('full_name', 'phone_number')
    filter_horizontal = ('commands',)
    def direction_name(self, obj): return obj.direction.name if obj.direction else "-"

# --- TASKS ---
@admin.register(ActivityTask)
class ActivityTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'points', 'get_visibility')
    list_filter = ('command',) 
    def get_visibility(self, obj):
        return f"🔒 {obj.command.title}" if obj.command else "🌍 ОБЩЕЕ"

# --- SUBMISSIONS ---
@admin.register(ActivitySubmission)
class ActivitySubmissionAdmin(admin.ModelAdmin):
    list_display = ('volunteer', 'task', 'status', 'created_at')
    list_filter = ('status', 'task__command')
    actions = ['approve_selected', 'reject_selected']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.role == 'admin':
            return qs
        return qs.filter(Q(task__command__leader=request.user) | Q(volunteer__direction__responsible=request.user)).distinct()

    @admin.action(description="✅ Одобрить")
    def approve_selected(self, request, queryset):
        for obj in queryset.filter(status='pending'):
            obj.status = 'approved'
            obj.save()

    @admin.action(description="❌ Отклонить")
    def reject_selected(self, request, queryset):
        for obj in queryset.filter(status='pending'):
            obj.status = 'rejected'
            obj.save()

admin.site.register(BotAccessConfig)
admin.site.register(VolunteerArchive)
