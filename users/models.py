import random
import string
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from directions.models import VolunteerDirection

class VolunteerManager(BaseUserManager):
    def create_user(self, login=None, password=None, **extra_fields):
        if login is None:
            base_login = extra_fields.get('name', 'user').lower().replace(" ", "")
            random_suffix = ''.join(random.choices(string.digits, k=4))
            login = f"{base_login}{random_suffix}"

        user = self.model(login=login, **extra_fields)

        if password is None:
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            user.visible_password = password

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, login, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(login, password, **extra_fields)


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
    
    # --- ДОБАВЛЕННЫЕ ПОЛЯ (для соответствия фронтенду) ---
    date_of_birth = models.DateField(verbose_name="Дата рождения", null=True, blank=True)
    place_of_study = models.CharField(max_length=255, verbose_name="Место учебы/работы", blank=True)
    choice_motives = models.TextField(verbose_name="Мотивы выбора направлений", blank=True)
    # -----------------------------------------------------

    why_volunteer = models.TextField(verbose_name="Почему Вы хотите стать волонтером?")
    volunteer_experience = models.TextField(verbose_name="Опыт волонтёрства")
    hobbies_skills = models.TextField(verbose_name="Навыки и хобби")
    strengths = models.TextField(verbose_name="Сильные качества")
    why_choose_you = models.TextField(verbose_name="Почему выбрать Вас?")

    agree_inactivity_removal = models.BooleanField(verbose_name="Согласны с удалением при низкой активности?")
    agree_terms = models.BooleanField(verbose_name="Согласны с условиями клуба?")
    ready_travel = models.BooleanField(verbose_name="Готовы к выездам?")
    ideas_improvements = models.TextField(verbose_name="Идеи и улучшения")
    expectations = models.TextField(verbose_name="Ожидания")

    directions = models.ManyToManyField(VolunteerDirection, verbose_name="Выбранные направления", blank=True)
    weekly_hours = models.CharField(max_length=50, verbose_name="Время в неделю")
    attend_meetings = models.BooleanField(verbose_name="Будете присутствовать на собраниях?")

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

    def save(self, *args, **kwargs):
        if not self.pk:
            if not self.login:
                base_login = self.name.lower().replace(" ", "")
                random_suffix = ''.join(random.choices(string.digits, k=4))
                self.login = f"{base_login}{random_suffix}"

            if not self.password:
                raw_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                self.visible_password = raw_password
                self.set_password(raw_password)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Волонтёр'
        verbose_name_plural = 'Волонтёры'


class VolunteerArchive(models.Model):
    full_name = models.CharField(max_length=200)
    email = models.EmailField(verbose_name='Email', blank=True, null=True)
    phone_number = models.CharField(max_length=50)
    photo = models.ImageField(upload_to='volunteers_archive_photos/', null=True, blank=True)
    why_volunteer = models.TextField()
    volunteer_experience = models.TextField()
    hobbies_skills = models.TextField()
    strengths = models.TextField()
    why_choose_you = models.TextField()
    directions = models.ManyToManyField(VolunteerDirection, blank=True)
    weekly_hours = models.CharField(max_length=50, blank=True)
    attend_meetings = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Архив волонтёра"
        verbose_name_plural = "Архив волонтёров"