import random
import string
import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.text import slugify
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db.models.functions import Coalesce

from directions.models import VolunteerDirection


# --- МЕНЕДЖЕР ПОЛЬЗОВАТЕЛЕЙ ---
class VolunteerManager(BaseUserManager):
    def create_user(self, login=None, password=None, **extra_fields):
        if not login:
            raise ValueError('Поле Логин должно быть заполнено')
        
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

class AppSettings(models.Model):
    is_direction_selection_open = models.BooleanField("Открыт выбор направлений", default=False)
    is_registration_open = models.BooleanField("Открыта регистрация", default=True) 
    is_points_submission_open = models.BooleanField("Открыта отправка баллов (отчетов)", default=True)

    class Meta:
        verbose_name = "Настройки системы"
        verbose_name_plural = "Настройки системы"

    def save(self, *args, **kwargs):
        if not self.pk and AppSettings.objects.exists():
            raise ValidationError('Может быть только одна запись с настройками')
        return super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

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

    preferred_directions = models.ManyToManyField(
        'directions.VolunteerDirection', 
        verbose_name="Желаемые направления (Выбор)", 
        related_name="preferring_volunteers", 
        blank=True
    )

    draft_direction = models.ForeignKey(
        'directions.VolunteerDirection', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='draft_volunteers'
    )

    point = models.DecimalField("Баллы", max_digits=10, decimal_places=1, default=0)
    point_goal = models.IntegerField("Цель (баллы)", default=100, help_text="Личная цель волонтера")
    yellow_card = models.IntegerField("Желтые карточки", default=0)

    is_staff = models.BooleanField("Доступ в админку", default=False)
    is_active = models.BooleanField("Активен", default=True)

    objects = VolunteerManager()

    USERNAME_FIELD = 'login'
    REQUIRED_FIELDS = []

    def generate_unique_login(self, base_name):
        base_login = base_name.lower().replace(" ", "").replace("ё", "e")
        while True:
            random_suffix = ''.join(random.choices(string.digits, k=4))
            login_candidate = f"user_{random_suffix}"
            if not Volunteer.objects.filter(login=login_candidate).exists():
                return login_candidate
            

    def save(self, *args, **kwargs):
        if not self.pk:
            if not self.login:
                base = self.name if self.name else "volunteer"
                self.login = self.generate_unique_login(base)
            if not self.password:
                raw_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                self.visible_password = raw_password
                self.set_password(raw_password)

        from directions.models import VolunteerDirection
        from commands.models import Command

        if self.pk:
            is_responsible = VolunteerDirection.objects.filter(responsible=self).exists()
            is_leader = Command.objects.filter(leader=self).exists()

            if is_responsible or is_leader:
                if self.role == 'volunteer':
                    self.role = 'curator'
                self.is_staff = True

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name or self.login} ({self.get_role_display()})"

    def has_perm(self, perm, obj=None):
        if self.is_active and self.is_superuser:
            return True
        return super().has_perm(perm, obj)
    
    def has_module_perms(self, app_label):
        if self.is_active and self.is_staff:
            return True
        return super().has_module_perms(app_label)

    class Meta:
        verbose_name = "Волонтер"
        verbose_name_plural = "Волонтеры"

# --- СИСТЕМА ЗАДАНИЙ И БАЛЛОВ ---
class ActivityTask(models.Model):
    title = models.CharField("Название (RU)", max_length=255)
    description = models.TextField("Описание (RU)", blank=True)
    
    title_en = models.CharField("Название (EN)", max_length=255, blank=True, null=True)
    description_en = models.TextField("Описание (EN)", blank=True, null=True)
    
    points = models.DecimalField("Баллы (базовые/макс)", max_digits=6, decimal_places=1, default=0)
    order = models.PositiveIntegerField("Порядок", default=0, help_text="Чем меньше число, тем выше задание в списке")

    is_flexible = models.BooleanField(
        "Гибкие баллы", 
        default=False, 
        help_text="Если включено, куратор сможет сам вписать количество баллов."
    )
    
    command = models.ForeignKey(
        'commands.Command', 
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
        dest = self.command.title if self.command else "ОБЩЕЕ"
        return f"[{dest}] {display_title} ({type_str})"

    class Meta:
        verbose_name = "Справочник заданий"
        verbose_name_plural = "Справочник заданий"
        ordering = ['order', 'title']

class ActivitySubmission(models.Model):
    STATUS_CHOICES = [
        ('pending', 'На проверке'),
        ('approved', 'Принято'),
        ('rejected', 'Отклонено'),
    ]

    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE, verbose_name="Волонтер", related_name="submissions")
    task = models.ForeignKey(ActivityTask, on_delete=models.CASCADE, verbose_name="Задание")
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='pending')
    
    command = models.ForeignKey(
        'commands.Command', 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        verbose_name="Команда (для тимлида)"
    )
    direction = models.ForeignKey(
        'directions.VolunteerDirection', 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        verbose_name="Направление (для куратора)"
    )

    date = models.DateField("Дата выполнения", default=timezone.now)
    points_awarded = models.DecimalField(
        "Начислено баллов", 
        max_digits=6, decimal_places=1, 
        null=True, blank=True
    )
    created_at = models.DateTimeField("Дата подачи", auto_now_add=True)
    description = models.TextField("Комментарий/Отчет", blank=True, null=True) 
    quantity = models.IntegerField(default=1)
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_status = None

        if not is_new:
            old_status = ActivitySubmission.objects.get(pk=self.pk).status

        super().save(*args, **kwargs)

        if is_new or old_status != self.status:
            recalc_volunteer_points(self.volunteer_id)

    def delete(self, *args, **kwargs):
        vol_id = self.volunteer_id
        super().delete(*args, **kwargs)

        if vol_id:
            recalc_volunteer_points(vol_id)



class Recruitment(models.Model):
    title = models.CharField("Название набора", max_length=255)
    slug = models.SlugField(
        "URL",
        unique=True,
        blank=True,
        max_length=255,
        allow_unicode=True,
        help_text="Генерируется автоматически"
    )
    description = models.TextField("Описание", blank=True)
    
    # 🕒 Поля для автоматического открытия и закрытия заявок
    start_date = models.DateTimeField("Начало набора", null=True, blank=True)
    end_date = models.DateTimeField("Конец набора (Дедлайн)", null=True, blank=True)

    class Meta:
        verbose_name = "Набор волонтеров"
        verbose_name_plural = "Наборы волонтеров"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title, allow_unicode=True)
            if not base_slug:
                base_slug = "recruitment-" + uuid.uuid4().hex[:6]

            slug = base_slug
            counter = 1
            while Recruitment.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
            
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class RecruitmentQuestion(models.Model):
    FIELD_TYPES = [
        ('short_text', 'Короткий текст'),
        ('long_text', 'Длинный текст'),
        ('number', 'Число'),
        ('photo', 'Фото'),
        ('video', 'Видео'),
        ('select', 'Одиночный выбор (Select)'),
        ('multiple_select', 'Множественный выбор (Несколько вариантов)'),
    ]

    recruitment = models.ForeignKey(
        Recruitment,
        related_name='questions',
        on_delete=models.CASCADE,
        verbose_name="Набор"
    )
    label = models.CharField("Текст вопроса", max_length=500)
    field_type = models.CharField("Тип поля", max_length=20, choices=FIELD_TYPES)
    required = models.BooleanField("Обязательный", default=True)
    order = models.PositiveIntegerField("Порядок", blank=True, null=True)

    # Опции вручную (если нужно написать свой список)
    options = models.JSONField(
        blank=True,
        default=list,
        help_text="Оставьте пустым, если хотите автоматически подгрузить направления из базы"
    )

    # 👈 НОВОЕ ПОЛЕ: Если вопрос требует выбора направления из VolunteerDirection
    use_directions_list = models.BooleanField(
        "Брать варианты из направлений (VolunteerDirection)?", 
        default=False,
        help_text="Если включено, варианты для select/multiple_select автоматически возьмутся из справочника направлений"
    )

    class Meta:
        verbose_name = "Вопрос анкеты"
        verbose_name_plural = "Вопросы анкеты"
        ordering = ['order']

    def save(self, *args, **kwargs):
        if self.order is None:
            last = RecruitmentQuestion.objects.filter(recruitment=self.recruitment).aggregate(
                models.Max('order')
            )['order__max'] or 0
            self.order = last + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.label


class RecruitmentApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('accepted', 'Принят'),
        ('rejected', 'Отклонен'),
    ]

    recruitment = models.ForeignKey(
        Recruitment,
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name="Набор"
    )

    volunteer = models.ForeignKey(
        'users.Volunteer', 
        on_delete=models.CASCADE, 
        related_name='recruitment_applications',
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
    
    # 👈 НОВОЕ ПОЛЕ: Флаг архивации
    is_archived = models.BooleanField("В архиве", default=False)
    
    created_at = models.DateTimeField("Дата подачи", auto_now_add=True)

    class Meta:
        verbose_name = "Заявка на набор"
        verbose_name_plural = "Заявки на наборы"

    def __str__(self):
        return f"Заявка #{self.id} на набор {self.recruitment.title}"


def recruitment_attachment_upload_to(instance, filename):
    ext = filename.split('.')[-1]
    name = uuid.uuid4().hex
    return f'recruitments/{instance.application.id}/{name}.{ext}'


class RecruitmentAttachment(models.Model):
    application = models.ForeignKey(
        RecruitmentApplication,
        related_name='files',
        on_delete=models.CASCADE,
        verbose_name="Заявка"
    )
    file = models.FileField("Файл", upload_to=recruitment_attachment_upload_to)
    label = models.CharField("Вопрос", max_length=255)

    class Meta:
        verbose_name = "Файл заявки"
        verbose_name_plural = "Файлы заявок"

    def __str__(self):
        return self.label

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
        unique_together = ('volunteer', 'direction', 'date')

class YellowCard(models.Model):
    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE, related_name='yellow_cards')
    issued_by = models.ForeignKey(Volunteer, on_delete=models.SET_NULL, null=True, related_name='issued_cards')
    date_issued = models.DateField(auto_now_add=True)
    reason = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Yellow Card for {self.volunteer.name}"
    
class ChatSession(models.Model):
    session_id = models.CharField(max_length=100, unique=True, verbose_name="ID Сессии")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Создано")

    class Meta:
        verbose_name = "Сессия чата"
        verbose_name_plural = "Сессии чата"

    def __str__(self):
        return f"Чат {self.session_id} от {self.created_at.strftime('%d.%m.%Y %H:%M')}"

class ChatMessage(models.Model):
    SENDER_CHOICES = (
        ('user', 'Пользователь'),
        ('ai', 'ИИ-Ассистент'),
    )
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages', verbose_name="Сессия")
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES, verbose_name="Отправитель")
    text = models.TextField(verbose_name="Сообщение")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Время")

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender}: {self.text[:50]}"

class MiniTeam(models.Model):
    title = models.CharField("Название мини-команды", max_length=255)
    
    direction = models.ForeignKey(
        'directions.VolunteerDirection', on_delete=models.CASCADE, 
        null=True, blank=True, related_name='mini_teams', verbose_name="Направление"
    )
    command = models.ForeignKey(
        'commands.Command', on_delete=models.CASCADE, 
        null=True, blank=True, related_name='mini_teams', verbose_name="Общая команда"
    )
    
    members = models.ManyToManyField(
        'Volunteer', 
        through='MiniTeamMembership', 
        through_fields=('miniteam', 'volunteer'),
        related_name='my_mini_teams'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Мини-команда"
        verbose_name_plural = "Мини-команды"

    def __str__(self):
        parent = self.direction.name if self.direction else (self.command.title if self.command else "Без привязки")
        return f"{self.title} ({parent})"

class MiniTeamMembership(models.Model):
    ROLE_CHOICES = [
        ('member', 'Волонтер (обзвонщик)'),
        ('mini_curator', 'Мини-куратор'),
        ('basist', 'Базист'),
    ]
    
    miniteam = models.ForeignKey(MiniTeam, on_delete=models.CASCADE, related_name='memberships')
    volunteer = models.ForeignKey('Volunteer', on_delete=models.CASCADE, related_name='miniteam_roles')
    role = models.CharField("Роль в мини-команде", max_length=20, choices=ROLE_CHOICES, default='member')
    assigned_by = models.ForeignKey('Volunteer', on_delete=models.SET_NULL, null=True, related_name='assigned_miniteam_roles')

    class Meta:
        verbose_name = "Участник мини-команды"
        verbose_name_plural = "Участники мини-команд"
        unique_together = ('miniteam', 'volunteer')

class SponsorTask(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает внимания'),
        ('review', 'На рассмотрении'),
        ('agreed', 'Соглашение'),
        ('rejected', 'Отказ'),
    ]
    
    miniteam = models.ForeignKey(MiniTeam, on_delete=models.CASCADE, related_name='sponsors')
    
    sponsor_name = models.CharField("Название/Имя спонсора", max_length=255)
    contact_info = models.TextField("Контактные данные (телефон, email, соцсети)")
        
    assigned_volunteer = models.ForeignKey(
        'Volunteer', on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='sponsor_tasks', verbose_name="Ответственный за обзвон"
    )
    
    status = models.CharField("Вердикт", max_length=20, choices=STATUS_CHOICES, default='pending')
    comment = models.TextField("Комментарий от волонтера", blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Спонсор / Задача"
        verbose_name_plural = "База спонсоров"
        ordering = ['-created_at']


from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from decimal import Decimal

def recalc_volunteer_points(volunteer_id):
    # Достаем все принятые заявки волонтера вместе с привязанными заданиями
    submissions = ActivitySubmission.objects.filter(
        volunteer_id=volunteer_id, 
        status='approved'
    ).select_related('task')
    
    total_points = Decimal('0.0')
    
    # Считаем баллы надежным способом через Python
    for sub in submissions:
        if sub.points_awarded is not None:
            # Если куратор или админ вписал свои баллы
            total_points += Decimal(str(sub.points_awarded))
        elif sub.task:
            # Если берем базовые баллы из задания, умножаем на количество
            qty = sub.quantity if sub.quantity else 1
            total_points += Decimal(str(sub.task.points)) * Decimal(str(qty))
            
    # Принудительно обновляем счет волонтера
    Volunteer.objects.filter(id=volunteer_id).update(point=total_points)
