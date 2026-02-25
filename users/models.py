import random
import string
from django.db import models
from django.dispatch import receiver
from django.utils import timezone   
# Добавляем Sum сюда:
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import DecimalField, Sum 
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from directions.models import VolunteerDirection 
from django.db.models.functions import Coalesce

# --- МЕНЕДЖЕР ПОЛЬЗОВАТЕЛЕЙ (Без изменений) ---
class VolunteerManager(BaseUserManager):
    def create_user(self, login=None, password=None, **extra_fields):
        if not login:
            raise ValueError('Поле Логин должно быть заполнено')
        
        user = self.model(login=login, **extra_fields)
        
        # Если пароль не пришел (автогенерация)
        if password is None:
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        
        # ТЕПЕРЬ пароль сохраняется в оба поля всегда:
        user.visible_password = password  # Для тебя (открытый текст)
        user.set_password(password)      # Для системы (хеш)
        
        user.save(using=self._db)
        return user
    
    def create_superuser(self, login, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(login, password, **extra_fields)


# --- МОДЕЛЬ ВОЛОНТЕРА (ПОЛЬЗОВАТЕЛЬ) ---
class Volunteer(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('volunteer', 'Волонтер'),
        ('teamlead', 'Тимлидер'),
        ('curator', 'Куратор'),
        ('president', 'Президент'),
        ('bailiff_base', 'Пристав (База)'),
        ('bailiff_activity', 'Пристав (Активности)'),
        ('equity_officer', 'Эквити-офицер'),
        ('admin', 'Администратор'),
    ]

    login = models.CharField("Логин", max_length=100, unique=True, blank=True)
    name = models.CharField("ФИО", max_length=255, blank=True, null=True)
    phone_number = models.CharField("Телефон", max_length=100, blank=True, null=True) 
    email = models.EmailField("Email", blank=True, null=True)    
    visible_password = models.CharField("Пароль (видимый)", max_length=100, blank=True)
    image = models.ImageField("Фото", upload_to="users/", blank=True)
    
    role = models.CharField("Роль (Статус)", max_length=20, choices=ROLE_CHOICES, default='volunteer')
    
    # Связи
    direction = models.ManyToManyField(VolunteerDirection, verbose_name="Направления", related_name="volunteers", blank=True)

    # Баллы и нарушения
    point = models.DecimalField("Баллы", max_digits=10, decimal_places=1, default=0)
    yellow_card = models.IntegerField("Желтые карточки", default=0)

    # Статусы
    is_staff = models.BooleanField("Доступ в админку", default=False)
    is_active = models.BooleanField("Активен", default=True)

    objects = VolunteerManager()

    USERNAME_FIELD = 'login'
    REQUIRED_FIELDS = []

    def generate_unique_login(self, base_name):
        # Очистка имени для логина (убираем пробелы, меняем ё)
        base_login = base_name.lower().replace(" ", "").replace("ё", "e")
        while True:
            random_suffix = ''.join(random.choices(string.digits, k=4))
            login_candidate = f"user_{random_suffix}"
            if not Volunteer.objects.filter(login=login_candidate).exists():
                return login_candidate
            
    def update_total_points(self):
            """Полный пересчет баллов на основе одобренных заявок"""
            # Coalesce берет points_awarded, а если там None -> берет task__points
            total = self.submissions.filter(status='approved').aggregate(
                total=Sum(
                    Coalesce('points_awarded', 'task__points', output_field=DecimalField())
                )
            )['total'] or 0
            
            self.point = total
            self.save(update_fields=['point'])

    def save(self, *args, **kwargs):
        # 1. Логика для новых записей
        if not self.pk:
            if not self.login:
                base = self.name if self.name else "volunteer"
                self.login = self.generate_unique_login(base)
            if not self.password:
                raw_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                self.visible_password = raw_password
                self.set_password(raw_password)

        # 2. Проверка лидерства и ответсвенности
        # Импорт внутри, чтобы избежать циклической зависимости
        from directions.models import VolunteerDirection
        from commands.models import Command

        # Если объект уже существует в БД
        if self.pk:
            is_responsible = VolunteerDirection.objects.filter(responsible=self).exists()
            is_leader = Command.objects.filter(leader=self).exists()

            if is_responsible or is_leader:
                # АВТО-ПОВЫШЕНИЕ: только если текущая роль - 'volunteer'
                if self.role == 'volunteer':
                    self.role = 'curator'
                
                # Доступ в админку обязателен для всех лидеров и кураторов
                self.is_staff = True

        # 3. ЕДИНСТВЕННЫЙ вызов super().save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name or self.login} ({self.get_role_display()})"

    def has_perm(self, perm, obj=None):
        # Суперпользователи имеют все права
        if self.is_active and self.is_superuser:
            return True
        # Остальные проверяются через PermissionsMixin (группы)
        return super().has_perm(perm, obj)
    
    def has_module_perms(self, app_label):
        # Разрешаем просмотр модулей, если у пользователя есть доступ в админку
        if self.is_active and self.is_staff:
            return True
        return super().has_module_perms(app_label)

    class Meta:
        verbose_name = "Волонтер"
        verbose_name_plural = "Волонтеры"

# --- СИСТЕМА ЗАДАНИЙ И БАЛЛОВ ---

class ActivityTask(models.Model):
    # Русские версии (основные)
    title = models.CharField("Название (RU)", max_length=255)
    description = models.TextField("Описание (RU)", blank=True)
    
    # Английские версии (необязательные)
    title_en = models.CharField("Название (EN)", max_length=255, blank=True, null=True)
    description_en = models.TextField("Описание (EN)", blank=True, null=True)
    
    points = models.DecimalField("Баллы (базовые/макс)", max_digits=6, decimal_places=1, default=0)
    
    is_flexible = models.BooleanField(
        "Гибкие баллы", 
        default=False, 
        help_text="Если включено, куратор сможет сам вписать количество баллов при одобрении."
    )
    
    command = models.ForeignKey(
        'commands.Command',  # <--- Используем строку вместо класса
        on_delete=models.CASCADE, 
        verbose_name="Спец. Команда (опционально)", 
        null=True, blank=True, 
        help_text="Если выбрать команду, задание будет видно ТОЛЬКО участникам этой команды."
    )

    def __str__(self):
        display_title = self.title
        if self.title_en:
            display_title += f" / {self.title_en}"
            
        type_str = "ГИБКОЕ" if self.is_flexible else f"{self.points} б."
        # Здесь тоже нужно быть аккуратным, если command None, ошибки не будет
        dest = self.command.title if self.command else "ОБЩЕЕ"
        return f"[{dest}] {display_title} ({type_str})"

    class Meta:
        verbose_name = "Справочник заданий"
        verbose_name_plural = "Справочник заданий"


from django.utils import timezone
from django.db import models, transaction
from django.db.models import F

class ActivitySubmission(models.Model):
    STATUS_CHOICES = [
        ('pending', 'На проверке'),
        ('approved', 'Принято'),
        ('rejected', 'Отклонено'),
    ]

    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE, verbose_name="Волонтер", related_name="submissions")
    task = models.ForeignKey(ActivityTask, on_delete=models.CASCADE, verbose_name="Задание")
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # --- КЛЮЧЕВЫЕ ПОЛЯ ДЛЯ МАРШРУТИЗАЦИИ ---
    # Если заполнено это поле -> видит Тимлид
    command = models.ForeignKey(
        'commands.Command', 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        verbose_name="Команда (для тимлида)"
    )
    # Если заполнено это поле (а команда пуста) -> видит Куратор
    direction = models.ForeignKey(
        'directions.VolunteerDirection', 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        verbose_name="Направление (для куратора)"
    )
    # ---------------------------------------

    date = models.DateField("Дата выполнения", default=timezone.now)
    points_awarded = models.DecimalField(
        "Начислено баллов", 
        max_digits=6, decimal_places=1, 
        null=True, blank=True
    )
    created_at = models.DateTimeField("Дата подачи", auto_now_add=True)
    description = models.TextField("Комментарий/Отчет", blank=True, null=True) 

    def save(self, *args, **kwargs):
        # Твоя логика с начислением баллов через save() рабочая, 
        # но помни про риск NULL в поле point у волонтера.
        if self.pk:
            old_instance = ActivitySubmission.objects.get(pk=self.pk)
            old_points = old_instance.points_awarded if old_instance.points_awarded is not None else old_instance.task.points
            new_points = self.points_awarded if self.points_awarded is not None else self.task.points

            if old_instance.status != 'approved' and self.status == 'approved':
                self.volunteer.point = (self.volunteer.point or 0) + new_points
            elif old_instance.status == 'approved' and self.status != 'approved':
                self.volunteer.point = (self.volunteer.point or 0) - old_points
            elif old_instance.status == 'approved' and self.status == 'approved':
                diff = new_points - old_points
                self.volunteer.point = (self.volunteer.point or 0) + diff

            self.volunteer.save(update_fields=['point'])
        
        else:
            if self.status == 'approved':
                points = self.points_awarded if self.points_awarded is not None else self.task.points
                self.volunteer.point = (self.volunteer.point or 0) + points
                self.volunteer.save(update_fields=['point'])

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.status == 'approved':
            points = self.points_awarded if self.points_awarded is not None else self.task.points
            self.volunteer.point = (self.volunteer.point or 0) - points
            self.volunteer.save(update_fields=['point'])
        super().delete(*args, **kwargs)

    class Meta:
        verbose_name = "Заявка на баллы"
        verbose_name_plural = "Заявки на баллы"
        ordering = ['-date']


# --- АНКЕТЫ (Остаются почти без изменений, только связи) ---

class VolunteerApplication(models.Model):
    full_name = models.CharField("ФИО", max_length=200)
    phone_number = models.CharField("Телефон", max_length=50)
    email = models.EmailField("Email", blank=True, null=True)
    photo = models.ImageField("Фото", upload_to='volunteers_photos/', null=True, blank=True)
    date_of_birth = models.DateField("Дата рождения", null=True, blank=True)
    place_of_study = models.CharField("Место учебы/работы", max_length=255, blank=True)
    
    choice_motives = models.TextField("Мотивы", blank=True)
    why_volunteer = models.TextField("Почему волонтер?", blank=True)
    volunteer_experience = models.TextField("Опыт", blank=True)
    hobbies_skills = models.TextField("Хобби", blank=True)
    strengths = models.TextField("Качества", blank=True)
    why_choose_you = models.TextField("Почему вы?", blank=True)
    ideas_improvements = models.TextField("Идеи", blank=True)
    expectations = models.TextField("Ожидания", blank=True)
    feedback = models.TextField("Фидбэк", blank=True, null=True)
    
    agree_inactivity_removal = models.BooleanField(default=False)
    agree_terms = models.BooleanField(default=False)
    ready_travel = models.BooleanField(default=False)
    attend_meetings = models.BooleanField(default=False)
    
    weekly_hours = models.CharField("Время в неделю", max_length=50, blank=True)

    status = models.CharField("Статус", max_length=20, choices=[('submitted', 'Отправлено'), ('interview', 'На собеседовании'), ('accepted', 'Принят'), ('rejected', 'Отказ')], default='submitted')
    volunteer_created = models.BooleanField(default=False, editable=False)
    volunteer = models.OneToOneField(Volunteer, on_delete=models.SET_NULL, null=True, blank=True, related_name="application_profile")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    direction = models.ForeignKey(
        'directions.VolunteerDirection', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=False,
        related_name='volunteer_applications'
    )

    commands = models.ManyToManyField(
                'commands.Command', # <--- Используем строку вместо класса
                related_name="volunteer_members", 
                blank=True
            )

    class Meta:
        verbose_name = "Анкета кандидата"
        verbose_name_plural = "Анкеты кандидатов"

# Архив и Бот
class VolunteerArchive(models.Model):
    full_name = models.CharField("ФИО", max_length=200)
    email = models.EmailField("Email", blank=True, null=True)
    phone_number = models.CharField("Телефон", max_length=50)
    photo = models.ImageField(upload_to='volunteers_archive_photos/', null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    why_volunteer = models.TextField(blank=True)
    directions = models.ManyToManyField(VolunteerDirection, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Архив волонтера"
        verbose_name_plural = "Архив волонтеров"

class BotAccessConfig(models.Model):
    role = models.CharField("Роль доступа", max_length=20, choices=[('volunteer', 'Волонтер'), ('curator', 'Куратор')], unique=True)
    password = models.CharField("Пароль доступа", max_length=128)

    class Meta:
        verbose_name = "Настройка доступа бота"
        verbose_name_plural = "Настройки доступа бота"

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'П (Присутствовал)'),
        ('late', 'Оп (Опоздал)'),
        ('excused', 'УП (Уважительная причина)'),
        ('absent', 'Н (Не было)'),
    ]

    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE, verbose_name="Волонтер", related_name="attendance_records")
    direction = models.ForeignKey('directions.VolunteerDirection', on_delete=models.CASCADE, verbose_name="Направление")
    date = models.DateField("Дата собрания")
    status = models.CharField("Статус", max_length=10, choices=STATUS_CHOICES)
    marked_by = models.ForeignKey(Volunteer, on_delete=models.SET_NULL, null=True, verbose_name="Кто отметил", related_name="marked_attendances")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Посещаемость"
        verbose_name_plural = "Журнал посещаемости"
        unique_together = ('volunteer', 'direction', 'date') # Один волонтер - одна отметка в день по направлению


class YellowCard(models.Model):
    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE, related_name='yellow_cards')
    issued_by = models.ForeignKey(Volunteer, on_delete=models.SET_NULL, null=True, related_name='issued_cards')
    date_issued = models.DateField(auto_now_add=True)
    reason = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Yellow Card for {self.volunteer.name}"
    
@receiver(post_save, sender=ActivitySubmission)
@receiver(post_delete, sender=ActivitySubmission)
def update_volunteer_points_on_submission_change(sender, instance, **kwargs):
    if instance.volunteer:
        # Вызываем твой метод, который считает только 'approved'
        instance.volunteer.update_total_points()