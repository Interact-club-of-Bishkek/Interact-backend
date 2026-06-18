from django.contrib import admin
from django.db.models import Q, Count
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    ChatSession, ChatMessage, Volunteer, VolunteerApplication, VolunteerArchive, 
    ActivityTask, ActivitySubmission, BotAccessConfig,
    Attendance, YellowCard, AppSettings, MiniTeam, MiniTeamMembership, SponsorTask
)

# --- НАСТРОЙКИ ШАПКИ АДМИНКИ ---
admin.site.site_header = "Управление Волонтерами"
admin.site.site_title = "Admin Panel"
admin.site.index_title = "Добро пожаловать в CRM"

@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    # Выводим все три рубильника в список
    list_display = (
        '__str__', 
        'is_registration_open', 
        'is_direction_selection_open', 
        'is_points_submission_open' # <-- Добавлено
    )
    
    # Делаем их редактируемыми без захода внутрь записи
    list_editable = (
        'is_registration_open', 
        'is_direction_selection_open', 
        'is_points_submission_open' # <-- Добавлено
    )

    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False
    
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
    # 1. Добавляем 'get_rank' самым первым в list_display
    list_display = ('get_rank', 'get_avatar', 'name_display', 'display_password', 'role_badge', 'point_display', 'is_active_icon')
    list_display_links = ('get_avatar', 'name_display')
    list_filter = ('role', 'is_active', 'direction')
    search_fields = ('name', 'login', 'phone_number', 'email')
    filter_horizontal = ('direction', 'groups', 'user_permissions')
    inlines = [YellowCardInline, ActivitySubmissionInline]
    
    # 2. Метод для вычисления места
    def get_rank(self, obj):
        # Подстраховка: если баллы пустые, считаем как 0
        current_points = obj.point or 0
        
        # Считаем, сколько волонтеров имеют СТРОГО БОЛЬШЕ баллов.
        # Если ни у кого нет больше баллов, запрос вернет 0. Значит 0 + 1 = 1-е место!
        higher_points_count = type(obj).objects.filter(point__gt=current_points).count()
        
        return f"{higher_points_count + 1}"
    
    # 3. Настройки колонки
    get_rank.short_description = 'Место'
    get_rank.admin_order_field = '-point'  # Делает заголовок кликабельным (сразу сортирует по баллам)

    # 🔥 ИСПРАВЛЕНИЕ: Добавляем кастомные методы сюда статично
    readonly_fields = ('last_login', 'get_avatar_large', 'yellow_card_count_display')

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
    
    # 🔥 Делаем колонку сортируемой по полю 'point' в БД
    point_display.admin_order_field = 'point' 
    point_display.short_description = 'Баллы' # Заодно даем красивое имя колонке

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
    list_filter = ('status', 'created_at', 'task', 'task__command')
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
    search_fields = ('title',)
    
    # Поля, отображаемые в списке
    list_display = ('order', 'title', 'points', 'visibility_icon', 'submissions_count')
    
    # 🔥 Указываем, что ссылкой будет 'title', а не первое поле ('order')
    list_display_links = ('title',)
    
    # Поля, которые можно редактировать прямо в списке
    list_editable = ('order',) 
    
    autocomplete_fields = ['command']

    def visibility_icon(self, obj):
        if obj.command:
            return format_html('🔒 <small>{}</small>', obj.command.title)
        return format_html('<span style="color: #10b981;">🌍 Общее</span>')
    visibility_icon.short_description = "Видимость"

    def submissions_count(self, obj):
        from django.urls import reverse
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

class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('sender', 'text', 'created_at')
    can_delete = False

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'created_at')
    inlines = [ChatMessageInline]


# Inline-класс для отображения участников прямо внутри страницы мини-команды
class MiniTeamMembershipInline(admin.TabularInline):
    model = MiniTeamMembership
    extra = 1  # Количество пустых строк для добавления новых участников
    raw_id_fields = ('volunteer', 'assigned_by') # Чтобы не грузить весь список волонтеров в dropdown


@admin.register(MiniTeam)
class MiniTeamAdmin(admin.ModelAdmin):
    list_display = ('title', 'get_parent_group', 'created_at')
    list_filter = ('direction', 'command')
    search_fields = ('title',)
    inlines = [MiniTeamMembershipInline] # Подключаем таблицу участников

    def get_parent_group(self, obj):
        """Показывает, к чему привязана мини-команда"""
        if obj.direction:
            return f"Направление: {obj.direction.name}"
        if obj.command:
            return f"Команда: {obj.command.title}"
        return "—"
    get_parent_group.short_description = "Привязка"


@admin.register(MiniTeamMembership)
class MiniTeamMembershipAdmin(admin.ModelAdmin):
    list_display = ('miniteam', 'volunteer', 'role', 'assigned_by')
    list_filter = ('role', 'miniteam')
    search_fields = ('volunteer__name', 'volunteer__login', 'miniteam__title')
    raw_id_fields = ('volunteer', 'miniteam', 'assigned_by')


@admin.register(SponsorTask)
class SponsorTaskAdmin(admin.ModelAdmin):
    list_display = ('sponsor_name', 'miniteam', 'assigned_volunteer', 'status', 'created_at')
    list_filter = ('status', 'miniteam')
    search_fields = ('sponsor_name', 'assigned_volunteer__name', 'assigned_volunteer__login')
    raw_id_fields = ('miniteam', 'assigned_volunteer')
    
    # Раскрашиваем статусы для красоты в админке
    def get_status_html(self, obj):
        colors = {
            'pending': 'orange',
            'review': 'blue',
            'agreed': 'green',
            'rejected': 'red'
        }
        color = colors.get(obj.status, 'black')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_status_display())
    get_status_html.short_description = 'Вердикт'