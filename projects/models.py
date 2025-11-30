from django.db import models
from directions.models import ProjectDirection
from logs.loggable_model import LoggableModel
from django.utils import timezone


class Project(LoggableModel):
    
    CATEGORY_CHOICES = [
        ("sport", "Спорт"),
        ("cyber_sport", "Киберспорт"),
        ("education", "Образование"),
        ("fundraising", "Фандрайзинг"),
        ("cultural", "Культура"),
    ]
    image = models.ImageField(verbose_name='Обложка', upload_to='project/')
    name = models.CharField(verbose_name='Название проекта', max_length=100)
    title = models.TextField(verbose_name='Описание проекта', max_length=5000)
    direction = models.ForeignKey(
        ProjectDirection,
        on_delete=models.CASCADE,
        verbose_name='Направление',
        related_name='projects',
        null=True,
        blank=True
    )    
    price = models.IntegerField(verbose_name='Цена', default=0)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, verbose_name='Категория')

    phone_number = models.CharField(max_length=50, verbose_name="Номер для записи")
    address = models.CharField(max_length=200, verbose_name="Адрес")

    time_start = models.DateTimeField(verbose_name="Время начало")
    time_end = models.DateTimeField(verbose_name="Время конца")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_archived = models.BooleanField(default=False, verbose_name='В архиве')

    @classmethod
    def archive_expired(cls):
        now = timezone.now()
        cls.objects.filter(time_end__lt=now, is_archived=False).update(is_archived=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Проект'
        verbose_name_plural = 'Проекты'


class YearResult(models.Model):
    sport = models.IntegerField(verbose_name='Спорт')
    cyber_sport = models.IntegerField(verbose_name='Киберспорт')
    education = models.IntegerField(verbose_name='Образование')
    fundraising = models.IntegerField(verbose_name='Фандрайзинг')
    cultural = models.IntegerField(verbose_name='Культура')
    total_amount = models.IntegerField(verbose_name='Общая сумма')

    class Meta:
        verbose_name = 'Результат года'
        verbose_name_plural = 'Результаты года'

