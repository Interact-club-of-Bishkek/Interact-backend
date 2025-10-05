from django.db import models

class VolunteerForm(models.Model):
    name = models.CharField(verbose_name='Фамилия Имя', max_length=100)
    phone_number = models.CharField(verbose_name='Номер телефона', max_length=100)
    image = models.ImageField(verbose_name='Фотография', upload_to="users/", blank=True)
    telegram_username = models.CharField(verbose_name='Telegram @username', max_length=100, blank=True)
    telegram_id = models.BigIntegerField(verbose_name='Telegram ID', blank=True, null=True)
    is_verified = models.BooleanField(default=False, verbose_name="Проверено")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Форму заявки'
        verbose_name_plural = 'Форма заявки'

#13

class VolunteerFormArchive(models.Model):
    name = models.CharField(verbose_name='Фамилия Имя', max_length=100)
    phone_number = models.CharField(verbose_name='Номер телефона', max_length=100)
    image = models.ImageField(verbose_name='Фотография', upload_to="users/", blank=True)
    telegram_username = models.CharField(verbose_name='Telegram @username', max_length=100, blank=True)
    telegram_id = models.BigIntegerField(verbose_name='Telegram ID', blank=True, null=True)
    moved_to = models.CharField(verbose_name="Куда перенесён", max_length=50, blank=True)

    def __str__(self):
        return f"{self.name} → {self.moved_to}"

    class Meta:
        verbose_name_plural = 'Архив заявок'



class WaitingList(models.Model):
    name = models.CharField(verbose_name='Фамилия Имя', max_length=100)
    phone_number = models.CharField(verbose_name='Номер телефона', max_length=100)
    image = models.ImageField(verbose_name='Фотография', upload_to="users/", blank=True)
    telegram_username = models.CharField(verbose_name='Telegram @username', max_length=100, blank=True)
    telegram_id = models.BigIntegerField(verbose_name='Telegram ID', blank=True, null=True)
    is_approved = models.BooleanField(default=False, verbose_name="Одобрен")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Отбор 1 этапа'


class MailingPending(models.Model):
    name = models.CharField(verbose_name='Фамилия Имя', max_length=100)
    phone_number = models.CharField(verbose_name='Номер телефона', max_length=100)
    image = models.ImageField(verbose_name='Фотография', upload_to="users/", blank=True)
    telegram_username = models.CharField(verbose_name="Telegram @username", max_length=100, blank=True)
    telegram_id = models.BigIntegerField(verbose_name='Telegram ID', blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Отбор 2 этапа'


class TextMailing(models.Model):
    text = models.TextField(max_length=3000)

    def __str__(self):
        return self.text
    
    class Meta:
        verbose_name = 'Текст'
        verbose_name_plural = 'Текст для 2 этапа'
