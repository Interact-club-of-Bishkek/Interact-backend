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


class Partner(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название партнера')
    logo = models.ImageField(upload_to='partners/', verbose_name='Логотип партнера')
    link = models.URLField(max_length=500, blank=True, null=True, verbose_name='Ссылка на сайт партнера')
    order = models.IntegerField(default=0, verbose_name='Порядок отображения')
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'Партнер'
        verbose_name_plural = 'Партнеры'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class HeroSlide(models.Model):
    badge = models.CharField(
        max_length=100, 
        verbose_name="Бейдж (надзаголовок)", 
        help_text="Например: Сезон 2025-2026"
    )
    title = models.CharField(
        max_length=200, 
        verbose_name="Заголовок"
    )
    description = models.TextField(
        verbose_name="Описание", 
        blank=True
    )
    image = models.ImageField(
        upload_to='hero_slides/', 
        verbose_name="Фоновое изображение"
    )
    
    # Настройки кнопки
    button_text = models.CharField(
        max_length=50, 
        verbose_name="Текст кнопки", 
        default="Подробнее"
    )
    button_url = models.CharField(
        max_length=255, 
        verbose_name="Ссылка кнопки", 
        help_text="Можно писать как относительные пути (volunteer.html), так и полные ссылки (https://...)"
    )
    
    # Служебные поля
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок сортировки")

    class Meta:
        verbose_name = "Слайд на главной"
        verbose_name_plural = "Слайды на главной"
        ordering = ['order']

    def __str__(self):
        return self.title
    

class YearResult(models.Model):
    year = models.IntegerField(verbose_name="Год", default=2026, unique=True) # <-- ДОБАВЛЕНО ПОЛЕ ГОДА
    sport = models.IntegerField(verbose_name='Спорт')
    cyber_sport = models.IntegerField(verbose_name='Киберспорт')
    education = models.IntegerField(verbose_name='Образование')
    fundraising = models.IntegerField(verbose_name='Фандрайзинг')
    cultural = models.IntegerField(verbose_name='Культура')
    total_amount = models.IntegerField(verbose_name='Общая сумма')

    class Meta:
        verbose_name = 'Результат года'
        verbose_name_plural = 'Результаты года'
        
    def __str__(self): # <-- ДОБАВЛЕНО
        return f"Статистика за {self.year} год"

# ... (HeroSlide остается без изменений, там __str__ есть) ...

class TeamMember(models.Model):
    full_name = models.CharField(max_length=255, verbose_name="ФИО")
    position = models.CharField(max_length=255, verbose_name="Должность")
    photo = models.ImageField(upload_to='team/', verbose_name="Фото")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Член команды"
        verbose_name_plural = "Команда"
        ordering = ['order']

    def __str__(self): # <-- ДОБАВЛЕНО
        return f"{self.full_name} ({self.position})"

class FAQ(models.Model):
    question = models.CharField(max_length=500, verbose_name="Вопрос")
    answer = models.TextField(verbose_name="Ответ")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Вопрос-ответ"
        verbose_name_plural = "FAQ"
        ordering = ['order']

    def __str__(self): # <-- ДОБАВЛЕНО
        return self.question