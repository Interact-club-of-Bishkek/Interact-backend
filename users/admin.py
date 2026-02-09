from django.contrib import admin
from django.db import models
from django.db.models import Q
from django.utils.html import format_html
from .models import (
    Volunteer, VolunteerApplication, VolunteerArchive, 
    ActivityTask, ActivitySubmission, BotAccessConfig,
    Attendance, YellowCard
)

# --- INLINES (Вложенные таблицы) ---

class ActivitySubmissionInline(admin.TabularInline):
    model = ActivitySubmission
    extra = 0
    verbose_name = "Выполненное задание"
    verbose_name_plural = "История заданий"
    readonly_fields = ('created_at',)
    fields = ('task', 'status', 'created_at')
    can_delete = False
    def has_add_permission(self, request, obj): return False

class YellowCardInline(admin.TabularInline):
    model = YellowCard
    fk_name = 'volunteer'  # <--- ДОБАВЬТЕ ЭТУ СТРОКУ
    extra = 0 
    readonly_fields = ('date_issued', 'issued_by') 
    can_delete = True
    verbose_name = "Желтая карточка"
    verbose_name_plural = "⚠️ Желтые карточки"

# --- YELLOW CARD ADMIN (Отдельный раздел) ---

@admin.register(YellowCard)
class YellowCardAdmin(admin.ModelAdmin):
    # Что показывать в списке
    list_display = ('volunteer', 'reason', 'issued_by', 'date_issued')
    
    # По каким полям можно искать
    search_fields = ('volunteer__name', 'volunteer__login', 'reason')
    
    # Фильтры справа
    list_filter = ('date_issued', 'issued_by')
    
    # Чтобы при выборе волонтера выпадал поиск, а не огромный список
    autocomplete_fields = ['volunteer', 'issued_by']


# --- VOLUNTEER ADMIN ---

@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('name', 'login', 'display_password', 'role', 'point', 'is_staff', 'is_active')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'direction')
    search_fields = ('name', 'login', 'phone_number')
        
    # Добавляем системные поля groups и permissions для удобного выбора
    filter_horizontal = ('direction', 'groups', 'user_permissions') 
    
    # ВАЖНО: Объединяем оба инлайна в один список!
    inlines = [ActivitySubmissionInline, YellowCardInline]
    
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
            'fields': ['direction']
        }),
        ('Статистика', {
            'fields': ('point',) # Убрал yellow_card отсюда, так как они теперь видны в inlines внизу
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

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('volunteer', 'direction', 'status_badge', 'date', 'marked_by_display')
    list_filter = ('date', 'direction', 'status')
    search_fields = ('volunteer__name', 'volunteer__login', 'volunteer__email')
    
    # Чтобы при выборе волонтера был удобный поиск, а не огромный список
    autocomplete_fields = ['volunteer', 'direction', 'marked_by']
    
    # Навигация по датам сверху
    date_hierarchy = 'date'

    # Красивое отображение статуса цветом
    def status_badge(self, obj):
        colors = {
            'present': 'green',
            'late': 'orange',
            'excused': 'blue',
            'absent': 'red',
        }
        labels = {
            'present': 'Присутствовал',
            'late': 'Опоздал',
            'excused': 'Уваж. причина',
            'absent': 'Не было',
        }
        color = colors.get(obj.status, 'black')
        label = labels.get(obj.status, obj.status)
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, label
        )
    status_badge.short_description = 'Статус'

    # Кто отметил (если поле заполнено)
    def marked_by_display(self, obj):
        return obj.marked_by.name if obj.marked_by and obj.marked_by.name else (obj.marked_by.login if obj.marked_by else "-")
    marked_by_display.short_description = 'Кто отметил'
    
    # Запрещаем менять "Кто отметил" вручную, чтобы сохранялась история (опционально)
    readonly_fields = ('created_at',)


admin.site.register(BotAccessConfig)
admin.site.register(VolunteerArchive)