from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Command, Question, Application, Attachment

# Позволяет видеть и добавлять вопросы прямо в команде
class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1

# Позволяет видеть загруженные файлы прямо в заявке
# Замени TabularStackedInline на StackedInline
class AttachmentInline(admin.StackedInline): 
    model = Attachment
    extra = 0
    readonly_fields = ('display_file',)

    def display_file(self, obj):
        if obj.file:
            # Если это картинка — показываем превью
            if obj.file.url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                return format_html('<img src="{}" style="max-height: 300px; border-radius: 10px;"/>', obj.file.url)
            # Если это видео
            elif obj.file.url.lower().endswith(('.mp4', '.mov', '.avi')):
                return format_html('<video src="{}" style="max-height: 300px;" controls></video>', obj.file.url)
            return format_html('<a href="{}" target="_blank">Открыть файл</a>', obj.file.url)
        return "Нет файла"
    display_file.short_description = "Просмотр медиа"

@admin.register(Command)
class CommandAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'start_date', 'end_date', 'get_full_url')
    prepopulated_fields = {"slug": ("title",)}
    inlines = [QuestionInline]
    
    # Ссылка на твой API (как мы делали раньше)
    def get_full_url(self, obj):
        url = reverse('command-detail', kwargs={'slug': obj.slug})
        return format_html('<a href="{0}" target="_blank">{0}</a>', url)
    get_full_url.short_description = "API URL"

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'command', 'status', 'created_at')
    list_filter = ('status', 'command')
    inlines = [AttachmentInline] # Показываем фото/видео внутри заявки
    readonly_fields = ('created_at', 'display_answers')
    
    # Красивый вывод JSON-ответов в админке
    def display_answers(self, obj):
        html = "<ul>"
        for question, answer in obj.answers.items():
            html += f"<li><b>{question}:</b> {answer}</li>"
        html += "</ul>"
        return format_html(html)
    display_answers.short_description = "Ответы пользователя"

@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'application', 'file', 'label')