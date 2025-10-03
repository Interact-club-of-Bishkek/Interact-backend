from django.db import models
from users.models import Direction
import datetime
import uuid

class Project(models.Model):
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
    direction = models.ForeignKey(Direction, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Направление')
    price = models.IntegerField(verbose_name='Цена', default=0)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, verbose_name='Категория')
    date = models.DateField(default=datetime.date.today, verbose_name='Дата')

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
