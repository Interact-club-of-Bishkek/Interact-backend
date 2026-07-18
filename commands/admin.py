from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Command, Question, Application, Attachment,
    BoardPosition, BoardApplication, BoardAttachment, BoardQuestion
)

# ==========================================
# INLINES (Вложенные формы)
# ==========================================

class QuestionInline(admin.StackedInline):
    model = Question
    extra = 0  
    
    fieldsets = (
        (None, {
            'fields': (
                ('order', 'required'),
                'label',
                'field_type'
            )
        }),
    )
    ordering = ('order',)
    verbose_name = "Вопрос"
    verbose_name_plural = "📝 Конструктор анкеты"


class BoardQuestionInline(admin.StackedInline):
    model = BoardQuestion
    extra = 0  
    
    fieldsets = (
        (None, {
            'fields': (
                ('order', 'required'),
                'label',
                'field_type'
            )
        }),
    )
    ordering = ('order',)
    verbose_name = "Вопрос для Борда"
    verbose_name_plural = "📝 Конструктор анкеты Борда"


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0
    fields = ('label', 'file', 'preview')
    readonly_fields = ('preview',)
    verbose_name = "Файл"
    verbose_name_plural = "📎 Вложения"

    def preview(self, obj):
        if not obj.file:
            return "—"
        url = obj.file.url.lower()
        if url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="height:50px; border-radius:5px; border:1px solid #ccc;"></a>',
                obj.file.url, obj.file.url
            )
        return format_html('<a href="{}" target="_blank" style="font-weight:bold;">📄 Скачать файл</a>', obj.file.url)
    preview.short_description = "Предпросмотр"


class BoardAttachmentInline(admin.TabularInline):
    model = BoardAttachment
    extra = 0
    fields = ('label', 'file', 'preview')
    readonly_fields = ('preview',)
    verbose_name = "Файл Борда"
    verbose_name_plural = "📎 Вложения Борда"

    def preview(self, obj):
        if not obj.file:
            return "—"
        url = obj.file.url.lower()
        if url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="height:50px; border-radius:5px; border:1px solid #ccc;"></a>',
                obj.file.url, obj.file.url
            )
        return format_html('<a href="{}" target="_blank" style="font-weight:bold;">📄 Скачать файл</a>', obj.file.url)
    preview.short_description = "Предпросмотр"


# ==========================================
# ADMINS ДЛЯ КОМАНД
# ==========================================

@admin.register(Command)
class CommandAdmin(admin.ModelAdmin):
    list_display = ('title', 'direction_badge', 'dates_display', 'volunteers_count', 'api_link_btn')
    list_filter = ('direction', 'start_date')
    search_fields = ('title', 'description')
    
    inlines = [QuestionInline] 
    filter_horizontal = ('volunteers',)
    save_on_top = True

    fieldsets = (
        ('📌 Основная информация', {
            'fields': ('title', 'slug', 'description') 
        }),
        ('👤 Управление', {
            'fields': ('leader', 'direction'),
            'description': 'Кто руководит и к какому направлению относится'
        }),
        ('📅 Сроки проведения', {
            'fields': (('start_date', 'end_date'),),
        }),
        ('👥 Участники', {
            'fields': ('volunteers',),
            'classes': ('collapse',),
        }),
    )

    def direction_badge(self, obj):
        if obj.direction:
            return format_html('<span style="background:#e0f2fe; color:#0369a1; padding:2px 6px; border-radius:4px;">{}</span>', obj.direction.name)
        return "—"
    direction_badge.short_description = "Направление"

    def dates_display(self, obj):
        s = obj.start_date.strftime('%d.%m') if obj.start_date else "..."
        e = obj.end_date.strftime('%d.%m.%Y') if obj.end_date else "..."
        return f"{s} — {e}"
    dates_display.short_description = "Даты"

    def volunteers_count(self, obj):
        count = obj.volunteers.count()
        return format_html('<b style="color:green;">{}</b> чел.', count)
    volunteers_count.short_description = "Участников"

    def api_link_btn(self, obj):
        if not obj.slug:
            return "-"
        try:
            url = reverse('command-detail', kwargs={'slug': obj.slug}) 
            return format_html('<a href="{}" target="_blank" style="background:#3b82f6; color:white; padding:3px 8px; border-radius:4px; text-decoration:none;">JSON</a>', url)
        except:
            return "-"
    api_link_btn.short_description = "API"


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'command_link', 'volunteer_display', 'status_badge', 'created_at')
    list_filter = ('status', 'command', 'created_at')
    search_fields = ('answers', 'command__title')
    readonly_fields = ('created_at', 'answers_table')
    inlines = [AttachmentInline]
    actions = ['mark_accepted', 'mark_rejected']

    fieldsets = (
        ('Инфо о заявке', {
            'fields': ('command', 'status', 'created_at')
        }),
        ('📋 Ответы анкеты', {
            'fields': ('answers_table',)
        }),
    )

    def command_link(self, obj):
        return obj.command.title
    command_link.short_description = "Команда"

    def volunteer_display(self, obj):
        if hasattr(obj, 'volunteer') and obj.volunteer:
            return f"{obj.volunteer.name} (@{obj.volunteer.login})"
        if obj.answers:
            try:
                first_val = list(obj.answers.values())[0]
                return str(first_val)
            except:
                pass
        return "Гость"
    volunteer_display.short_description = "Кандидат"

    def status_badge(self, obj):
        colors = {'pending': '#f59e0b', 'accepted': '#10b981', 'rejected': '#ef4444'}
        labels = {'pending': '⏳ Ожидает', 'accepted': '✅ Принят', 'rejected': '❌ Отказ'}
        return format_html('<span style="background:{}; color:white; padding:4px 8px; border-radius:12px; font-weight:bold;">{}</span>', colors.get(obj.status, '#666'), labels.get(obj.status, obj.status))
    status_badge.short_description = "Статус"

    def answers_table(self, obj):
        if not obj.answers:
            return "Нет ответов"
        html = '<table style="width:100%; border-collapse: collapse;">'
        for k, v in obj.answers.items():
            label = k
            if k.startswith('q_') or k.isdigit():
                q_id = k.replace('q_', '')
                if q_id.isdigit():
                    q = Question.objects.filter(id=q_id).first()
                    if q: label = q.label
            html += f'<tr style="border-bottom: 1px solid #eee;"><td style="padding: 8px; width: 40%; color: #666; font-weight: bold;">{label}</td><td style="padding: 8px;">{v}</td></tr>'
        html += '</table>'
        return format_html(html)
    answers_table.short_description = "Ответы пользователя"

    @admin.action(description="Принять выбранные заявки")
    def mark_accepted(self, request, queryset):
        queryset.update(status='accepted')

    @admin.action(description="Отклонить выбранные заявки")
    def mark_rejected(self, request, queryset):
        queryset.update(status='rejected')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('label_short', 'command', 'field_type_badge', 'required', 'order')
    list_filter = ('command', 'field_type', 'required')
    list_editable = ('order', 'required')
    ordering = ('command', 'order')
    search_fields = ('label',)

    def label_short(self, obj):
        return (obj.label[:50] + '..') if len(obj.label) > 50 else obj.label
    label_short.short_description = "Вопрос"

    def field_type_badge(self, obj):
        return format_html('<span style="font-family:monospace; background:#f3f4f6; padding:2px 4px; border-radius:3px;">{}</span>', obj.field_type)
    field_type_badge.short_description = "Тип поля"


# ==========================================
# ADMINS ДЛЯ БОРДА
# ==========================================

@admin.register(BoardPosition)
class BoardPositionAdmin(admin.ModelAdmin):
    list_display = ('title', 'dates_display', 'members_count', 'api_link_btn')
    search_fields = ('title', 'description')
    filter_horizontal = ('members',)
    inlines = [BoardQuestionInline]  # Подключили конструктор вопросов
    save_on_top = True

    fieldsets = (
        ('📌 Основная информация', {
            'fields': ('title', 'slug', 'description') # Убрали JSON questions
        }),
        ('👤 Управление', {
            'fields': ('leader',)
        }),
        ('📅 Сроки проведения', {
            'fields': (('start_date', 'end_date'),),
        }),
        ('👥 Участники Борда', {
            'fields': ('members',),
            'classes': ('collapse',),
        }),
    )

    def dates_display(self, obj):
        s = obj.start_date.strftime('%d.%m') if obj.start_date else "..."
        e = obj.end_date.strftime('%d.%m.%Y') if obj.end_date else "..."
        return f"{s} — {e}"
    dates_display.short_description = "Даты"

    def members_count(self, obj):
        count = obj.members.count()
        return format_html('<b style="color:#6366f1;">{}</b> чел.', count)
    members_count.short_description = "В составе"

    def api_link_btn(self, obj):
        if not obj.slug:
            return "-"
        try:
            url = reverse('board-detail', kwargs={'slug': obj.slug}) 
            return format_html('<a href="{}" target="_blank" style="background:#3b82f6; color:white; padding:3px 8px; border-radius:4px; text-decoration:none;">JSON</a>', url)
        except:
            return "-"
    api_link_btn.short_description = "API"


@admin.register(BoardApplication)
class BoardApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'board_link', 'applicant_display', 'status_badge', 'created_at')
    list_filter = ('status', 'board_position', 'created_at')
    search_fields = ('answers', 'board_position__title', 'applicant__name', 'applicant__login')
    readonly_fields = ('created_at', 'answers_table')
    inlines = [BoardAttachmentInline]
    actions = ['mark_accepted', 'mark_rejected']

    fieldsets = (
        ('Инфо о заявке', {
            'fields': ('board_position', 'applicant', 'status', 'created_at')
        }),
        ('📋 Ответы анкеты', {
            'fields': ('answers_table',)
        }),
    )

    def board_link(self, obj):
        return obj.board_position.title
    board_link.short_description = "Позиция в Борде"

    def applicant_display(self, obj):
        if obj.applicant:
            return f"{obj.applicant.name} (@{obj.applicant.login})"
        return "Неизвестно"
    applicant_display.short_description = "Кандидат"

    def status_badge(self, obj):
        colors = {'pending': '#f59e0b', 'accepted': '#10b981', 'rejected': '#ef4444'}
        labels = {'pending': '⏳ Ожидает', 'accepted': '✅ Принят', 'rejected': '❌ Отказ'}
        return format_html('<span style="background:{}; color:white; padding:4px 8px; border-radius:12px; font-weight:bold;">{}</span>', colors.get(obj.status, '#666'), labels.get(obj.status, obj.status))
    status_badge.short_description = "Статус"

    def answers_table(self, obj):
        if not obj.answers:
            return "Нет ответов"
        
        html = '<table style="width:100%; border-collapse: collapse;">'
        for k, v in obj.answers.items():
            label = k
            if k.startswith('q_') or k.isdigit():
                q_id = k.replace('q_', '')
                if q_id.isdigit():
                    # Берем названия из новой модели BoardQuestion
                    q = BoardQuestion.objects.filter(id=q_id).first()
                    if q: label = q.label
            
            html += f'''
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; width: 40%; color: #666; font-weight: bold;">{label}</td>
                    <td style="padding: 8px;">{v}</td>
                </tr>
            '''
        html += '</table>'
        return format_html(html)
    answers_table.short_description = "Ответы пользователя"

    @admin.action(description="Принять выбранные заявки в Борд")
    def mark_accepted(self, request, queryset):
        for app in queryset:
            app.status = 'accepted'
            app.board_position.members.add(app.applicant)
            app.save()

    @admin.action(description="Отклонить выбранные заявки в Борд")
    def mark_rejected(self, request, queryset):
        queryset.update(status='rejected')


@admin.register(BoardQuestion)
class BoardQuestionAdmin(admin.ModelAdmin):
    list_display = ('label_short', 'board_position', 'field_type_badge', 'required', 'order')
    list_filter = ('board_position', 'field_type', 'required')
    list_editable = ('order', 'required')
    ordering = ('board_position', 'order')
    search_fields = ('label',)

    def label_short(self, obj):
        return (obj.label[:50] + '..') if len(obj.label) > 50 else obj.label
    label_short.short_description = "Вопрос"

    def field_type_badge(self, obj):
        return format_html('<span style="font-family:monospace; background:#f3f4f6; padding:2px 4px; border-radius:3px;">{}</span>', obj.field_type)
    field_type_badge.short_description = "Тип поля"


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('preview_thumb', 'label', 'application_link')
    search_fields = ('label',)

    def preview_thumb(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">📂 Файл</a>', obj.file.url)
        return "-"
    preview_thumb.short_description = "Файл"

    def application_link(self, obj):
        return format_html('<a href="/admin/commands/application/{}/change/">Заявка #{}</a>', obj.application.id, obj.application.id)
    application_link.short_description = "К заявке"


@admin.register(BoardAttachment)
class BoardAttachmentAdmin(admin.ModelAdmin):
    list_display = ('preview_thumb', 'label', 'application_link')
    search_fields = ('label',)

    def preview_thumb(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">📂 Файл</a>', obj.file.url)
        return "-"
    preview_thumb.short_description = "Файл"

    def application_link(self, obj):
        if obj.application:
            return format_html('<a href="/admin/commands/boardapplication/{}/change/">Заявка #{}</a>', obj.application.id, obj.application.id)
        return "-"
    application_link.short_description = "К заявке"