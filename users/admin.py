from django.contrib import admin
from django.db import models
from django.db.models import Q
from django.utils.html import format_html  # КРИТИЧЕСКИЙ ИМПОРТ (без него будет 500)
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

    def has_add_permission(self, request, obj):
        return False

@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    # Что видим в общем списке
    list_display = ('name', 'login', 'display_password', 'role', 'point', 'yellow_card', 'is_active')
    list_filter = ('role', 'is_active', 'direction', 'commands')
    search_fields = ('name', 'login', 'phone_number')
    
    # login оставляем только для чтения, чтобы не сломать связи, 
    # а visible_password УБИРАЕМ из readonly, чтобы его можно было менять!
    readonly_fields = ('login',) 
    
    filter_horizontal = ('direction', 'commands') 
    inlines = [ActivitySubmissionInline]
    
    fieldsets = (
        ('Учетные данные', {
            'fields': (('login', 'visible_password'), 'role', 'is_active')
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

    # ГЛАВНАЯ ФУНКЦИЯ: Синхронизация пароля
    def save_model(self, request, obj, form, change):
        """
        Эта функция срабатывает при нажатии кнопки 'Сохранить'.
        Если пароль в поле visible_password был изменен, мы его хешируем для системы.
        """
        # Если это новый пользователь или поле visible_password было изменено вручную
        if not change or 'visible_password' in form.changed_data:
            if obj.visible_password:
                obj.set_password(obj.visible_password)
        
        super().save_model(request, obj, form, change)

    # КРАСИВЫЙ ВЫВОД: Пароль в списке
    def display_password(self, obj):
        if obj.visible_password:
            return format_html(
                '<code style="background: #fdf2f2; padding: 3px 6px; border-radius: 4px; color: #d63384; font-weight: bold;">{}</code>',
                obj.visible_password
            )
        return format_html('<span style="color: #999;">Не задан</span>')
    
    display_password.short_description = "Пароль"

# --- APPLICATIONS ---
@admin.register(VolunteerApplication)
class VolunteerApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'direction_name', 'status', 'phone_number', 'created_at')
    list_filter = ('status', 'direction')
    search_fields = ('full_name', 'phone_number')
    filter_horizontal = ('commands',)

    def direction_name(self, obj):
        return obj.direction.name if obj.direction else "-"
    direction_name.short_description = "Направление"

# --- TASKS ---
@admin.register(ActivityTask)
class ActivityTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'points', 'get_visibility')
    list_filter = ('command',) 
    search_fields = ('title',)

    def get_visibility(self, obj):
        if obj.command:
            return f"🔒 Только команда: {obj.command.title}"
        return "🌍 ОБЩЕЕ (Видно всем)"
    get_visibility.short_description = "Видимость"

# --- SUBMISSIONS ---
@admin.register(ActivitySubmission)
class ActivitySubmissionAdmin(admin.ModelAdmin):
    list_display = ('volunteer', 'task', 'status', 'created_at')
    list_filter = ('status', 'task__command')
    search_fields = ('volunteer__name', 'task__title')
    actions = ['approve_selected', 'reject_selected']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.role == 'admin':
            return qs
        return qs.filter(
            Q(task__command__leader=request.user) | 
            Q(volunteer__direction__responsible=request.user)
        ).distinct()

    @admin.action(description="✅ Одобрить и начислить баллы")
    def approve_selected(self, request, queryset):
        for obj in queryset.filter(status='pending'):
            obj.status = 'approved'
            obj.save()

    @admin.action(description="❌ Отклонить выбранные")
    def reject_selected(self, request, queryset):
        for obj in queryset.filter(status='pending'):
            obj.status = 'rejected'
            obj.save()

# --- OTHER ---
admin.site.register(BotAccessConfig)
admin.site.register(VolunteerArchive)
