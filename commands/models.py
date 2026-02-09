from django.db import models
from django.utils.text import slugify
import uuid
import os
from directions.models import VolunteerDirection  # Импортируй модель направлений

class Command(models.Model):
    title = models.CharField("Название команды", max_length=255)
    slug = models.SlugField(
        "URL",
        unique=True,
        blank=True,
        max_length=255,
        allow_unicode=True,
        help_text="Генерируется автоматически"
    )
    description = models.TextField("Описание", blank=True)
    start_date = models.DateTimeField("Начало набора", null=True, blank=True)
    end_date = models.DateTimeField("Конец набора", null=True, blank=True)

    direction = models.ForeignKey(
        VolunteerDirection,
        on_delete=models.CASCADE,
        related_name="commands",
        verbose_name="Направление",
        null=True,
        blank=True
    )

    leader = models.ForeignKey(
        'users.Volunteer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Лидер/Куратор команды",
        related_name="led_commands"
    )

    # 🔥 ВОТ ЭТО ПОЛЕ
    volunteers = models.ManyToManyField(
            'users.Volunteer',
            related_name='volunteer_commands', # Это имя будет использоваться у волонтера
            blank=True,
            verbose_name="Участники команды",
            db_table="users_volunteer_commands" # СТРОГО УКАЗЫВАЕМ ТАБЛИЦУ ИЗ SQL
        )

    class Meta:
        verbose_name = "Команда"
        verbose_name_plural = "Команды"

    def save(self, *args, **kwargs):
        if not self.slug:
            # Генерируем слаг из заголовка. allow_unicode=True сохранит кириллицу.
            base_slug = slugify(self.title, allow_unicode=True)
            
            # Если заголовок пустой или состоит из символов, которые slugify удалил
            if not base_slug:
                base_slug = "command-" + uuid.uuid4().hex[:6]

            slug = base_slug
            counter = 1
            # Проверка уникальности
            while Command.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
            
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Question(models.Model):
    FIELD_TYPES = [
        ('short_text', 'Короткий текст'),
        ('long_text', 'Длинный текст'),
        ('number', 'Число'),
        ('photo', 'Фото'),
        ('video', 'Видео'),
        ('select', 'Выбор'),
    ]

    command = models.ForeignKey(
        Command,
        related_name='questions',
        on_delete=models.CASCADE,
        verbose_name="Команда"
    )
    label = models.CharField("Текст вопроса", max_length=500)
    field_type = models.CharField("Тип поля", max_length=20, choices=FIELD_TYPES)
    required = models.BooleanField("Обязательный", default=True)
    order = models.PositiveIntegerField("Порядок", blank=True, null=True)

    options = models.JSONField(
        blank=True,
        default=list,
        help_text="Только для select: список вариантов"
    )

    class Meta:
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"
        ordering = ['order']

    def save(self, *args, **kwargs):
        if self.order is None:
            last = Question.objects.filter(command=self.command).aggregate(
                models.Max('order')
            )['order__max'] or 0
            self.order = last + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.label


class Application(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('accepted', 'Принят'),
    ]

    command = models.ForeignKey(
        Command,
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name="Команда"
    )

    volunteer = models.ForeignKey(
        'users.Volunteer', 
        on_delete=models.CASCADE, 
        related_name='command_applications', # Заявки волонтера
        verbose_name="Волонтер",
        null=True 
    )


    answers = models.JSONField("Ответы")
    status = models.CharField(
        "Статус",
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField("Дата подачи", auto_now_add=True)

    class Meta:
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"

    def __str__(self):
        return f"Заявка #{self.id}"


def attachment_upload_to(instance, filename):
    ext = filename.split('.')[-1]
    name = uuid.uuid4().hex
    return f'applications/{instance.application.id}/{name}.{ext}'


class Attachment(models.Model):
    application = models.ForeignKey(
        Application,
        related_name='files',
        on_delete=models.CASCADE,
        verbose_name="Заявка"
    )
    file = models.FileField("Файл", upload_to=attachment_upload_to)
    label = models.CharField("Вопрос", max_length=255)

    class Meta:
        verbose_name = "Файл"
        verbose_name_plural = "Файлы"

    def __str__(self):
        return self.label