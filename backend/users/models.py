import random
import string
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

class VolunteerManager(BaseUserManager):
    def create_user(self, login, password=None, **extra_fields):
        if not login:
            raise ValueError('Login is required')
        login = login.lower()
        user = self.model(login=login, **extra_fields)
        if password is None:
            # Генерация пароля, если не передан
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            user.visible_password = password
        user.set_password(password)
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


class Direction(models.Model):
    name = models.CharField(verbose_name='Направление', max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Направление'
        verbose_name_plural = 'Направления'


class Volunteer(AbstractBaseUser, PermissionsMixin):
    login = models.CharField(verbose_name='Логин', max_length=100, unique=True, blank=True)
    visible_password = models.CharField(max_length=100, blank=True, editable=False, verbose_name='Пароль (видимый)')
    name = models.CharField(verbose_name='Фамилия Имя', max_length=100)
    phone_number = models.CharField(verbose_name='Номер телефона', max_length=100)
    image = models.ImageField(verbose_name='Фотография', upload_to="users/", blank=True)
    telegram_username = models.CharField(verbose_name='Telegram @username', max_length=100, blank=True)
    telegram_id = models.BigIntegerField(verbose_name='Telegram ID', blank=True, null=True)
    board = models.BooleanField(default=False)
    direction = models.ManyToManyField(Direction, verbose_name='Направление', related_name='volunteers', blank=True)
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
        verbose_name = 'Волонтера'
        verbose_name_plural = 'Волонтеры'
