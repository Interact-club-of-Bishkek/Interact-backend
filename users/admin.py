from django.contrib import admin
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
    readonly_fields = ('created_at', 'status', 'points_awarded', 'description', 'task')
    fields = ('task', 'status', 'points_awarded', 'description', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj):
        return False  # запрет добавления через inline

class YellowCardInline(admin.TabularInline):
    model = YellowCard
    fk_name = 'volunteer'
    extra = 0
    readonly_fields = ('date_issued', 'issued_by')
    can_delete = True
    verbose_name = "Желтая карточка"
    verbose_name_plural = "⚠️ Желтые карточки"

# --- YELLOW CARD ADMIN ---
@admin.register(YellowCard)
class YellowCardAdmin(admin.ModelAdmin):
    list_display = ('volunteer', 'reason', 'issued_by', 'date_issued')
    search_fields = ('volunteer__name', 'volunteer__login', 'reason')
    list_filter = ('date_issued', 'issued_by')
    autocomplete_fields = ['volunteer', 'issued_by']

# --- VOLUNTEER ADMIN ---
@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('name', 'login', 'display_password', 'role', 'point', 'is_staff', 'is_active')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'direction')
    search_fields = ('name', 'login', 'phone_number')
    filter_horizontal = ('direction', 'groups', 'user_permissions', 'volunteer_commands')    
    inlines = [ActivitySubmissionInline, YellowCardInline]

    fieldsets = (
        ('Учетные данные', {
            'fields': (('login', 'visible_password'), 'role')
        }),
        ('Статусы доступа', {
            'fields': (('is_active', 'is_staff', 'is_superuser'),),
            'description': '<b>is_staff</b> — доступ в админку, <b>is_superuser</b> — полные права.'
        }),
        ('Личные данные', {
            'fields': ('name', 'phone_number', 'email', 'image')
        }),
        ('Структура', {
            'fields': ['direction']
        }),
        ('Статистика', {
            'fields': ('point',)
        }),
        ('Расширенные права', {
            'fields': ('groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        # Синхронизация видимого пароля
        if not change or 'visible_password' in form.changed_data:
            if obj.visible_password:
                obj.set_password(obj.visible_password)
        # Авто-назначение прав по роли
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
        return f"🔒 {obj.command.title}" if obj.command else "🌍 ОБЩЕЕ"
    get_visibility.short_description = "Доступность"

# --- SUBMISSIONS ---
@admin.register(ActivitySubmission)
class ActivitySubmissionAdmin(admin.ModelAdmin):
    list_display = ('volunteer', 'task', 'status', 'points_awarded', 'created_at')
    list_filter = ('status', 'task__command')
    actions = ['approve_selected', 'reject_selected']
    autocomplete_fields = ['volunteer', 'task']

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

# --- ATTENDANCE ---
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('volunteer', 'direction', 'status_badge', 'date', 'marked_by_display')
    list_filter = ('date', 'direction', 'status')
    search_fields = ('volunteer__name', 'volunteer__login', 'volunteer__email')
    autocomplete_fields = ['volunteer', 'direction', 'marked_by']
    date_hierarchy = 'date'
    readonly_fields = ('created_at',)

    def status_badge(self, obj):
        colors = {'present': 'green', 'late': 'orange', 'excused': 'blue', 'absent': 'red'}
        labels = {'present': 'Присутствовал', 'late': 'Опоздал', 'excused': 'Уваж. причина', 'absent': 'Не было'}
        color = colors.get(obj.status, 'black')
        label = labels.get(obj.status, obj.status)
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, label)
    status_badge.short_description = 'Статус'

    def marked_by_display(self, obj):
        if obj.marked_by:
            return obj.marked_by.name or obj.marked_by.login
        return "-"
    marked_by_display.short_description = 'Кто отметил'

# --- BOT CONFIG & ARCHIVE ---
admin.site.register(BotAccessConfig)
admin.site.register(VolunteerArchive)
