from django.contrib import admin
from django.db.models import Q, Count
from django.utils.html import format_html
from django.urls import reverse
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
        return obj.task.title if obj.task else "-"
    task_link.short_description = "Задание"

    def status_colored(self, obj):
        colors = {'pending': '#f59e0b', 'approved': '#10b981', 'rejected': '#ef4444'}
        return format_html(
            '<span style="color: white; background: {}; padding: 3px 8px; border-radius: 10px; font-weight: bold; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#6b7280'), obj.get_status_display()
        )

class YellowCardInline(admin.TabularInline):
    model = YellowCard
    fk_name = 'volunteer'
    extra = 0
    readonly_fields = ('date_issued', 'issued_by')
    fields = ('reason', 'issued_by', 'date_issued')
    can_delete = True
    classes = ('collapse',)

# --- ADMIN CLASSES ---

@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    # 🔥 ВЕРНУЛ display_password в список
    list_display = ('get_avatar', 'name_display', 'display_password', 'role_badge', 'point_display', 'is_active_icon')
    list_display_links = ('get_avatar', 'name_display')
    list_filter = ('role', 'is_active', 'direction')
    search_fields = ('name', 'login', 'phone_number', 'email')
    filter_horizontal = ('direction', 'groups', 'user_permissions')
    inlines = [YellowCardInline, ActivitySubmissionInline]
    readonly_fields = ('last_login',) 
    save_on_top = True

    fieldsets = (
        ('👤 Основная информация', {
            'fields': (('image', 'get_avatar_large'), ('name', 'login'), 'phone_number', 'email')
        }),
        ('🔑 Доступ и Роль', {
            'fields': (('role', 'visible_password'), ('is_active', 'is_staff', 'is_superuser')),
        }),
        ('🏆 Геймификация', {
            'fields': ('point', 'direction', 'yellow_card_count_display'),
        }),
        ('⚙️ Техническая информация', {
            'fields': ('last_login', 'groups', 'user_permissions'), 
            'classes': ('collapse',),
        }),
    )

    # 🔥 ФУНКЦИЯ ДЛЯ ВЫВОДА ПАРОЛЯ
    def display_password(self, obj):
        if obj.visible_password:
            return format_html(
                '<code style="background: rgba(214, 51, 132, 0.1); padding: 2px 6px; border-radius: 4px; color: #e83e8c; font-weight: bold; border: 1px solid rgba(214, 51, 132, 0.2);">{}</code>',
                obj.visible_password
            )
        return "—"
    display_password.short_description = "Пароль"

    def get_avatar(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 35px; height: 35px; border-radius: 50%; object-fit: cover;" />', obj.image.url)
        return "👤"

    def get_avatar_large(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 200px; border-radius: 10px;" />', obj.image.url)
        return "Нет фото"

    def name_display(self, obj):
        return format_html('<b>{}</b><br><span style="color: #888; font-size: 11px;">@{}</span>', obj.name, obj.login)

    def role_badge(self, obj):
        colors = {'admin': '#7c3aed', 'curator': '#2563eb', 'volunteer': '#059669'}
        return format_html(
            '<span style="background: {}; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 10px; text-transform: uppercase;">{}</span>',
            colors.get(obj.role, '#6b7280'), obj.get_role_display()
        )

    def point_display(self, obj):
        return format_html('<span style="color: #f59e0b; font-weight: bold;">★ {}</span>', obj.point)

    def is_active_icon(self, obj):
        return "✅" if obj.is_active else "❌"

    def yellow_card_count_display(self, obj):
        cnt = obj.yellow_cards.count()
        color = "#ef4444" if cnt > 0 else "#10b981"
        return format_html('<span style="color: {}; font-weight: bold; font-size: 14px;">{}</span>', color, cnt)
    
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


@admin.register(ActivitySubmission)
class ActivitySubmissionAdmin(admin.ModelAdmin):
    list_display = ('volunteer_display', 'task_display', 'status_badge', 'points_awarded', 'created_at')
    list_filter = ('status', 'created_at', 'task__command')
    search_fields = ('volunteer__name', 'task__title')
    autocomplete_fields = ['volunteer', 'task']
    actions = ['approve_selected', 'reject_selected']

    # 🔥 ВЕРНУЛ ОГРАНИЧЕНИЕ ВИДИМОСТИ ДЛЯ КУРАТОРОВ
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.role == 'admin':
            return qs
        return qs.filter(
            Q(task__command__leader=request.user) | 
            Q(volunteer__direction__responsible=request.user)
        ).distinct()

    def volunteer_display(self, obj):
        return obj.volunteer.name
    
    def task_display(self, obj):
        return obj.task.title

    def status_badge(self, obj):
        colors = {'pending': '#f59e0b', 'approved': '#10b981', 'rejected': '#ef4444'}
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 12px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#666'), obj.get_status_display()
        )

    @admin.action(description="✅ Одобрить")
    def approve_selected(self, request, queryset):
        queryset.filter(status='pending').update(status='approved')

    @admin.action(description="❌ Отклонить")
    def reject_selected(self, request, queryset):
        queryset.filter(status='pending').update(status='rejected')


@admin.register(ActivityTask)
class ActivityTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'points', 'visibility_icon', 'submissions_count')
    autocomplete_fields = ['command']

    def visibility_icon(self, obj):
        if obj.command:
            return format_html('🔒 <small>{}</small>', obj.command.title)
        return format_html('<span style="color: #10b981;">🌍 Общее</span>')

    # 🔥 ВЕРНУЛ СТАТИСТИКУ ОТВЕТОВ
    def submissions_count(self, obj):
        count = ActivitySubmission.objects.filter(task=obj).count()
        url = reverse("admin:users_activitysubmission_changelist") + f"?task__id__exact={obj.id}"
        return format_html('<a href="{}" style="font-weight: bold; color: #3b82f6;">{} ответов</a>', url, count)
    submissions_count.short_description = "Ответы"


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('volunteer', 'direction', 'status', 'date', 'marked_by')
    autocomplete_fields = ['volunteer', 'direction', 'marked_by']
    date_hierarchy = 'date'


@admin.register(YellowCard)
class YellowCardAdmin(admin.ModelAdmin):
    list_display = ('volunteer', 'reason', 'issued_by', 'date_issued')
    autocomplete_fields = ['volunteer', 'issued_by']


@admin.register(VolunteerApplication)
class VolunteerApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'direction', 'status', 'created_at')


admin.site.register(BotAccessConfig)
admin.site.register(VolunteerArchive)