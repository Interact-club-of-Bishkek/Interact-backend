from django.db import models
from users.models import Direction
# Create your models here.
class Project(models.Model):
    name = models.CharField(verbose_name='Название проекта', max_length=100)
    title = models.TextField(verbose_name='Описание проекта', max_length=5000)
    directions = models.ManyToManyField(Direction, verbose_name='Направление')
    image = models.ImageField(verbose_name='Фотография', upload_to='project/')

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Проект'
        verbose_name_plural = 'Проекты'