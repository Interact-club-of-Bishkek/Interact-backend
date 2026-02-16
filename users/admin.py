from django.contrib import admin
from django.db.models import Q, Count
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Volunteer, VolunteerApplication, VolunteerArchive, 
    ActivityTask, ActivitySubmission, BotAccessConfig,
    Attendance, YellowCard
)

# --- НАСТРОЙКИ ШАПКИ АДМИНКИ ---
admin.site.site_header = "Управление Волонтерами"
admin.site.site_title = "Admin Panel"
admin.site.index_title = "Добро пожаловать в CRM"

# --- INLINES ---

class ActivitySubmissionInline(admin.TabularInline):
    model = ActivitySubmission
    extra = 0
    verbose_name = "Задание"
    verbose_name_plural = "История выполнения заданий"
    fields = ('task_link', 'status_colored', 'points_awarded', 'description', 'created_at')
    readonly_fields = ('task_link', 'status_colored', 'created_at', 'points_awarded', 'description')
    can_delete = False
    show_change_link = True

    def task_link(self, obj):
        if obj.task:
            return obj.task.title
        return "-"
    task_link.short_description = "Задание"

    def status_colored(self, obj):
        colors = {
            'pending': '#f59e0b',   # Orange
            'approved': '#10b981',  # Green
            'rejected': '#ef4444',  # Red
        }
        return format_html(
            '<span style="color: white; background: {}; padding: 3px 8px; border-radius: 10px; font-weight: bold; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#6b7280'),
            obj.get_status_display()
        )
    status_colored.short_description = "Статус"

class YellowCardInline(admin.TabularInline):
    model = YellowCard
    fk_name = 'volunteer'
    extra = 0
    readonly_fields = ('date_issued', 'issued_by')
    fields = ('reason', 'issued_by', 'date_issued')
    can_delete = True
    verbose_name = "Нарушение"
    verbose_name_plural = "⚠️ Выданные предупреждения"
    classes = ('collapse',)

# --- ADMIN CLASSES ---

@admin.register(YellowCard)
class YellowCardAdmin(admin.ModelAdmin):
    list_display = ('volunteer_link', 'reason', 'issued_by_link', 'date_issued')
    search_fields = ('volunteer__name', 'reason')
    list_filter = ('date_issued',)
    autocomplete_fields = ['volunteer', 'issued_by']
    
    def volunteer_link(self, obj):
        return format_html('<a href="/admin/users/volunteer/{}/change/">👤 {}</a>', obj.volunteer.id, obj.volunteer.name)
    volunteer_link.short_description = "Волонтер"

    def issued_by_link(self, obj):
        if obj.issued_by:
            return format_html('👮‍♂️ {}', obj.issued_by.name or obj.issued_by.login)
        return "-"
    issued_by_link.short_description = "Кто выдал"

@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('get_avatar', 'name_display', 'role_badge', 'point_display', 'is_active_icon')
    list_display_links = ('get_avatar', 'name_display')
    list_filter = ('role', 'is_active', 'direction')
    search_fields = ('name', 'login', 'phone_number', 'email')
    filter_horizontal = ('direction', 'groups', 'user_permissions')
    inlines = [YellowCardInline, ActivitySubmissionInline]
    
    # ИСПРАВЛЕНИЕ: Убрали date_joined
    readonly_fields = ('last_login',) 
    save_on_top = True

    fieldsets = (
        ('👤 Основная информация', {
            'fields': (
                ('image', 'get_avatar_large'),
                ('name', 'login'),
                ('phone_number', 'email')
            )
        }),
        ('🔑 Доступ и Роль', {
            'fields': (
                ('role', 'visible_password'),
                ('is_active', 'is_staff', 'is_superuser'),
            ),
            'classes': ('wide',), 
        }),
        ('🏆 Геймификация и Структура', {
            'fields': ('point', 'direction', 'yellow_card_count_display'),
            'description': 'Баллы и направления деятельности'
        }),
        ('⚙️ Техническая информация', {
            # ИСПРАВЛЕНИЕ: Убрали date_joined
            'fields': ('last_login', 'groups', 'user_permissions'), 
            'classes': ('collapse',),
        }),
    )

    def get_avatar(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 35px; height: 35px; border-radius: 50%; object-fit: cover;" />', obj.image.url)
        return format_html('<div style="width: 35px; height: 35px; border-radius: 50%; background: #ddd; display: flex; align-items: center; justify-content: center;">👤</div>')
    get_avatar.short_description = "Фото"

    def get_avatar_large(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 200px; border-radius: 10px;" />', obj.image.url)
        return "Нет фото"
    get_avatar_large.short_description = "Предпросмотр"

    def name_display(self, obj):
        return format_html('<b>{}</b><br><span style="color: #666; font-size: 11px;">@{}</span>', obj.name, obj.login)
    name_display.short_description = "Пользователь"

    def role_badge(self, obj):
        colors = {'admin': '#7c3aed', 'curator': '#2563eb', 'volunteer': '#059669'}
        return format_html(
            '<span style="background: {}; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 10px; text-transform: uppercase;">{}</span>',
            colors.get(obj.role, '#6b7280'), obj.get_role_display()
        )
    role_badge.short_description = "Роль"

    def point_display(self, obj):
        return format_html('<span style="color: #d97706; font-weight: bold;">★ {}</span>', obj.point)
    point_display.short_description = "Баллы"

    def is_active_icon(self, obj):
        return "✅" if obj.is_active else "❌"
    is_active_icon.short_description = "Активен"

    def yellow_card_count_display(self, obj):
        cnt = obj.yellow_cards.count()
        color = "red" if cnt > 0 else "green"
        return format_html('<span style="color: {}; font-weight: bold; font-size: 14px;">{}</span>', color, cnt)
    yellow_card_count_display.short_description = "Кол-во нарушений"
    
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('get_avatar_large', 'yellow_card_count_display')
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        if not change or 'visible_password' in form.changed_data:
            if obj.visible_password:
                obj.set_password(obj.visible_password)
        if obj.role == 'admin':
            obj.is_staff = True
        super().save_model(request, obj, form, change)


@admin.register(VolunteerApplication)
class VolunteerApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'direction_badge', 'status_colored', 'phone_number', 'created_at')
    list_filter = ('status', 'direction')
    search_fields = ('full_name', 'phone_number')
    actions = ['approve_application']

    def direction_badge(self, obj):
        if obj.direction:
            return format_html('<span style="border: 1px solid #ccc; padding: 2px 5px; border-radius: 4px;">{}</span>', obj.direction.name)
        return "-"
    direction_badge.short_description = "Направление"

    def status_colored(self, obj):
        colors = {'pending': 'orange', 'accepted': 'green', 'rejected': 'red'}
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'), obj.get_status_display()
        )
    status_colored.short_description = "Статус"

    @admin.action(description="Принять в команду (Создать волонтера)")
    def approve_application(self, request, queryset):
        count = 0
        for app in queryset:
            # Логика создания
            count += 1
        self.message_user(request, f"Обработано заявок: {count}")


@admin.register(ActivityTask)
class ActivityTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'points', 'visibility_icon', 'submissions_count')
    list_filter = ('command', 'is_flexible')
    search_fields = ('title',)
    autocomplete_fields = ['command']

    def visibility_icon(self, obj):
        if obj.command:
            return format_html('🔒 <span style="color: #666;">{}</span>', obj.command.title)
        return format_html('🌍 <span style="color: green;">Общее</span>')
    visibility_icon.short_description = "Доступ"

    def submissions_count(self, obj):
        count = ActivitySubmission.objects.filter(task=obj).count()
        url = reverse("admin:users_activitysubmission_changelist") + f"?task__id__exact={obj.id}"
        return format_html('<a href="{}" style="font-weight: bold;">{} ответов</a>', url, count)
    submissions_count.short_description = "Статистика"


@admin.register(ActivitySubmission)
class ActivitySubmissionAdmin(admin.ModelAdmin):
    list_display = ('volunteer_display', 'task_display', 'status_badge', 'points_awarded', 'created_at')
    list_filter = ('status', 'created_at', 'task__command')
    search_fields = ('volunteer__name', 'task__title')
    autocomplete_fields = ['volunteer', 'task']
    actions = ['approve_selected', 'reject_selected']
    date_hierarchy = 'created_at'

    def volunteer_display(self, obj):
        return format_html('<b>{}</b>', obj.volunteer.name)
    volunteer_display.short_description = "Волонтер"

    def task_display(self, obj):
        return obj.task.title
    task_display.short_description = "Задание"

    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',
            'approved': '#10b981',
            'rejected': '#ef4444'
        }
        icons = {
            'pending': '⏳',
            'approved': '✅',
            'rejected': '❌'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 12px; font-weight: bold;">{} {}</span>',
            colors.get(obj.status, '#666'),
            icons.get(obj.status, ''),
            obj.get_status_display()
        )
    status_badge.short_description = "Статус"

    @admin.action(description="✅ Одобрить выбранные")
    def approve_selected(self, request, queryset):
        rows_updated = queryset.update(status='approved')
        self.message_user(request, f"Одобрено заявок: {rows_updated}")

    @admin.action(description="❌ Отклонить выбранные")
    def reject_selected(self, request, queryset):
        rows_updated = queryset.update(status='rejected')
        self.message_user(request, f"Отклонено заявок: {rows_updated}")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('volunteer_link', 'direction', 'status_badge', 'date', 'marked_by_display')
    list_filter = ('date', 'direction', 'status')
    search_fields = ('volunteer__name', 'volunteer__login')
    autocomplete_fields = ['volunteer', 'direction', 'marked_by']
    date_hierarchy = 'date'

    def volunteer_link(self, obj):
        return obj.volunteer.name
    volunteer_link.short_description = "Участник"

    def status_badge(self, obj):
        styles = {
            'present': 'background: #dcfce7; color: #166534; border: 1px solid #86efac;', 
            'late': 'background: #ffedd5; color: #9a3412; border: 1px solid #fdba74;',    
            'excused': 'background: #dbeafe; color: #1e40af; border: 1px solid #93c5fd;', 
            'absent': 'background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5;',  
        }
        return format_html(
            '<span style="padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; {}">{}</span>',
            styles.get(obj.status, ''),
            obj.get_status_display()
        )
    status_badge.short_description = "Посещаемость"
    
    def marked_by_display(self, obj):
        return obj.marked_by.name if obj.marked_by else "—"
    marked_by_display.short_description = "Отметил"

# --- ПРОЧЕЕ ---
admin.site.register(BotAccessConfig)
admin.site.register(VolunteerArchive)