from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Command, Question, Application, Attachment


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1
    fields = ('order', 'label', 'field_type', 'required')
    ordering = ('order',)
    verbose_name = "Вопрос"
    verbose_name_plural = "Вопросы"


class AttachmentInline(admin.StackedInline):
    model = Attachment
    extra = 0
    readonly_fields = ('preview',)
    verbose_name = "Файл"
    verbose_name_plural = "Файлы"

    def preview(self, obj):
        if not obj.file:
            return "—"
        url = obj.file.url.lower()
        if url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            return format_html(
                '<img src="{}" style="max-height:250px;border-radius:10px;">',
                obj.file.url
            )
        if url.endswith(('.mp4', '.mov', '.avi')):
            return format_html(
                '<video src="{}" controls style="max-height:250px;"></video>',
                obj.file.url
            )
        return format_html('<a href="{}" target="_blank">Открыть файл</a>', obj.file.url)

    preview.short_description = "Предпросмотр"


@admin.register(Command)
class CommandAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_date', 'end_date', 'api_link')
    search_fields = ('title',)
    inlines = [QuestionInline]

    def api_link(self, obj):
        url = reverse('command-detail', kwargs={'slug': obj.slug})
        return format_html('<a href="{}" target="_blank">Открыть API</a>', url)

    api_link.short_description = "API"


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'command', 'status', 'created_at')
    list_filter = ('status', 'command')
    readonly_fields = ('created_at', 'answers_view')
    inlines = [AttachmentInline]

    def answers_view(self, obj):
        html = "<ul>"
        for k, v in obj.answers.items():
            html += f"<li><b>{k}</b>: {v}</li>"
        html += "</ul>"
        return format_html(html)

    answers_view.short_description = "Ответы"


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('label', 'command', 'field_type', 'required', 'order')
    list_filter = ('command', 'field_type', 'required')
    list_editable = ('required', 'order')
    ordering = ('command', 'order')


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'application', 'label', 'file')
