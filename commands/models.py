from django.db import models

class Command(models.Model):
    title = models.CharField("Название команды", max_length=255)
    slug = models.SlugField("URL (slug)", unique=True)
    description = models.TextField("Полное описание", blank=True)
    start_date = models.DateTimeField("Начало набора", null=True, blank=True)
    end_date = models.DateTimeField("Конец набора", null=True, blank=True)

    def __str__(self):
        return self.title

class Question(models.Model):
    FIELD_TYPES = [
        ('short_text', 'Короткий текст'),
        ('long_text', 'Длинный текст'),
        ('number', 'Число'),
        ('photo', 'Фото'),
        ('video', 'Видео'),
        ('select', 'Выбор из направлений'), # Добавляем этот тип
    ]   
    command = models.ForeignKey(Command, related_name='questions', on_delete=models.CASCADE)
    label = models.CharField("Текст вопроса", max_length=500)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

class Application(models.Model):
    STATUS_CHOICES = [('pending', 'Ожидает'), ('accepted', 'Принят')]
    command = models.ForeignKey(Command, on_delete=models.CASCADE, related_name='applications')
    answers = models.JSONField("Текстовые ответы") # Здесь храним только текст
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

class Attachment(models.Model):
    application = models.ForeignKey(Application, related_name='files', on_delete=models.CASCADE)
    file = models.FileField(upload_to='applications/%Y/%m/%d/')
    label = models.CharField(max_length=255) # К какому вопросу файл