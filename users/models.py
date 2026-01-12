import random
import string
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
# Проверяем, что VolunteerDirection импортирован корректно
from directions.models import VolunteerDirection 


# --- Менеджер для кастомного пользователя (Volunteer) ---
class VolunteerManager(BaseUserManager):
    """Кастомный менеджер для модели Volunteer."""

    def create_user(self, login=None, password=None, **extra_fields):
        # Если login не передан, он будет сгенерирован в методе save() модели Volunteer
        
        # Защита от создания без обязательных полей
        if 'name' not in extra_fields:
            raise ValueError('The Name field must be set')
        
        user = self.model(login=login, **extra_fields)

        # Логика генерации пароля перенесена сюда, чтобы убедиться, что visible_password 
        # и password (hashed) установлены при создании через Manager.
        if password is None:
            raw_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            user.visible_password = raw_password
            user.set_password(raw_password)
        else:
            user.set_password(password)
            # Если пароль передан, visible_password обычно не устанавливается, 
            # но для админки его можно оставить пустым или установить переданный пароль, 
            # если это необходимо для логирования (но это небезопасно). Оставляем как есть.
            
        user.save(using=self._db)
        return user

    def create_superuser(self, login, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(login, password, **extra_fields)


# --- Модель Заявки кандидата ---
class VolunteerApplication(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Отправлено'),
        ('interview', 'На собеседовании'),
        ('accepted', 'Принят'),
        ('rejected', 'Отказ'),
    ]

    full_name = models.CharField(max_length=200, verbose_name="ФИО")
    email = models.EmailField(verbose_name='Email', blank=True, null=True)
    phone_number = models.CharField(max_length=50, verbose_name="Телефон")
    photo = models.ImageField(upload_to='volunteers_photos/', verbose_name="Фото", null=True, blank=True)
    
    # --- ИСПРАВЛЕННЫЕ И ДОБАВЛЕННЫЕ ПОЛЯ ---
    date_of_birth = models.DateField(verbose_name="Дата рождения", null=True, blank=True)
    place_of_study = models.CharField(max_length=255, verbose_name="Место учебы/работы", blank=True)
    choice_motives = models.TextField(verbose_name="Мотивы выбора направлений", blank=True)
    # ----------------------------------------

    why_volunteer = models.TextField(verbose_name="Почему Вы хотите стать волонтером?")
    volunteer_experience = models.TextField(verbose_name="Опыт волонтёрства")
    hobbies_skills = models.TextField(verbose_name="Навыки и хобби")
    strengths = models.TextField(verbose_name="Сильные качества")
    why_choose_you = models.TextField(verbose_name="Почему выбрать Вас?")

    agree_inactivity_removal = models.BooleanField(verbose_name="Согласны с удалением при низкой активности?")
    agree_terms = models.BooleanField(verbose_name="Согласны с условиями клуба?")
    ready_travel = models.BooleanField(verbose_name="Готовы к выездам?")
    ideas_improvements = models.TextField(verbose_name="Идеи и улучшения", blank=True) # Добавлено blank=True на всякий случай
    expectations = models.TextField(verbose_name="Ожидания")

    directions = models.ManyToManyField(VolunteerDirection, verbose_name="Выбранные направления", blank=True)
    weekly_hours = models.CharField(max_length=50, verbose_name="Время в неделю")
    attend_meetings = models.BooleanField(verbose_name="Будете присутствовать на собраниях?")
    
    feedback = models.TextField(verbose_name="Фидбэк (отзыв об анкете)", blank=True, null=True) # Добавлено поле для фидбэка из бота

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    volunteer_created = models.BooleanField(default=False, editable=False)
    volunteer = models.OneToOneField(
        'Volunteer',
        verbose_name='Созданный волонтёр',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='application'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "Анкета кандидата"
        verbose_name_plural = "Анкеты кандидатов"


# --- Модель Волонтёра (Кастомный пользователь) ---
class Volunteer(AbstractBaseUser, PermissionsMixin):
    login = models.CharField(verbose_name='Логин', max_length=100, unique=True, blank=True)
    visible_password = models.CharField(max_length=100, blank=True, editable=False, verbose_name='Пароль (видимый)')
    name = models.CharField(verbose_name='ФИО', max_length=100)
    phone_number = models.CharField(verbose_name='Телефон', max_length=100)
    email = models.EmailField(verbose_name='Email', blank=True)
    image = models.ImageField(verbose_name='Фото', upload_to="users/", blank=True)
    telegram_username = models.CharField(verbose_name='Telegram @username', max_length=100, blank=True)
    telegram_id = models.BigIntegerField(verbose_name='Telegram ID', blank=True, null=True)
    board = models.BooleanField(default=False)
    direction = models.ManyToManyField(
        VolunteerDirection,
        verbose_name='Направление',
        related_name='volunteers',
        blank=True
    )    
    point = models.IntegerField(verbose_name='Баллы', blank=True, null=True, default=0)
    yellow_card = models.IntegerField(verbose_name='Желтая карточка', blank=True, null=True, default=0)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = VolunteerManager()

    USERNAME_FIELD = 'login'
    REQUIRED_FIELDS = ['name', 'phone_number']

    def generate_unique_login(self, base_name):
        base_login = base_name.lower().replace(" ", "").replace("ё", "е")
        while True:
            random_suffix = ''.join(random.choices(string.digits, k=4))
            login_candidate = f"{base_login[:96]}{random_suffix}" # Ограничение длины
            if not Volunteer.objects.filter(login=login_candidate).exists():
                return login_candidate

    def save(self, *args, **kwargs):
            if not self.pk:
                # Если логин пустой, генерируем его
                if not self.login:
                    self.login = self.generate_unique_login(self.name)
                
                # Если пароля нет (даже захешированного), создаем его
                if not self.password:
                    raw_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                    self.visible_password = raw_password
                    self.set_password(raw_password)
            
            # Важно: вызываем родительский метод
            super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Волонтёр'
        verbose_name_plural = 'Волонтёры'


# --- Модель Архива волонтёра ---
class VolunteerArchive(models.Model):
    # Я добавил поля, которых не было в архиве, но которые были в заявке
    full_name = models.CharField(max_length=200)
    email = models.EmailField(verbose_name='Email', blank=True, null=True)
    phone_number = models.CharField(max_length=50)
    photo = models.ImageField(upload_to='volunteers_archive_photos/', null=True, blank=True)
    
    # --- ДОБАВЛЕННЫЕ ПОЛЯ В АРХИВ ---
    date_of_birth = models.DateField(verbose_name="Дата рождения", null=True, blank=True)
    place_of_study = models.CharField(max_length=255, verbose_name="Место учебы/работы", blank=True)
    choice_motives = models.TextField(verbose_name="Мотивы выбора направлений", blank=True)
    # --------------------------------
    
    why_volunteer = models.TextField()
    volunteer_experience = models.TextField()
    hobbies_skills = models.TextField()
    strengths = models.TextField()
    why_choose_you = models.TextField(blank=True) # Добавил blank=True
    
    weekly_hours = models.CharField(max_length=50, blank=True)
    attend_meetings = models.BooleanField(default=False)

    directions = models.ManyToManyField(VolunteerDirection, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "Архив волонтёра"
        verbose_name_plural = "Архив волонтёров"


from django.db import models

class BotAccessConfig(models.Model):
    ROLE_CHOICES = [
        ('volunteer', 'Волонтер (Только команды)'),
        ('curator', 'Куратор (Полный доступ)'),
    ]

    role = models.CharField("Роль", max_length=20, choices=ROLE_CHOICES, unique=True)
    password = models.CharField("Пароль доступа", max_length=128)

    class Meta:
        verbose_name = "Доступ бота"
        verbose_name_plural = "Доступы бота"

    def __str__(self):
        return self.get_role_display()