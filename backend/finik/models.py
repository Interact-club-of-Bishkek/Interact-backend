from django.db import models
from projects.models import Project
import uuid

class Payment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Ожидает оплаты"),
        ("success", "Успешно"),
        ("failed", "Неудачно"),
    ]
    payment_id = models.CharField("Номер платежа", max_length=100, unique=True)
    amount = models.DecimalField("Сумма", max_digits=10, decimal_places=2)
    comment = models.CharField("Комментарий", max_length=255, blank=True, null=True)
    first_name = models.CharField("Имя", max_length=100)
    last_name = models.CharField("Фамилия", max_length=100)
    phone = models.CharField("Телефон", max_length=20)
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.amount} сом ({self.status})"

    class Meta:
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"


class ProjectPayment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Ожидает оплаты"),
        ("success", "Успешно"),
        ("failed", "Неудачно"),
    ]
    payment_id = models.UUIDField("Номер платежа", default=uuid.uuid4, editable=False, unique=True)
    project = models.ForeignKey(Project, verbose_name="Проект", on_delete=models.CASCADE, related_name="payments")
    first_name = models.CharField("Имя", max_length=100, blank=True, null=True)
    last_name = models.CharField("Фамилия", max_length=100, blank=True, null=True)
    phone = models.CharField("Телефон", max_length=20, blank=True, null=True)
    comment = models.TextField("Комментарий", blank=True, null=True)
    amount = models.DecimalField("Сумма", max_digits=10, decimal_places=2)
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )
    payment_url = models.URLField("Ссылка на оплату", blank=True, null=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    def __str__(self):
        return f"[{self.project.name}] {self.first_name} {self.last_name} - {self.status}"

    class Meta:
        verbose_name = "Платёж проекта"
        verbose_name_plural = "Платежи проектов"


class PaymentLog(models.Model):
    LEVEL_CHOICES = (
        ("INFO", "Информация"),
        ("WARNING", "Предупреждение"),
        ("ERROR", "Ошибка"),
    )
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    level = models.CharField("Уровень", max_length=20, choices=LEVEL_CHOICES)
    message = models.TextField("Сообщение")
    extra = models.JSONField("Дополнительно", null=True, blank=True)

    def __str__(self):
        return f"[{self.created_at}] {self.level}: {self.message[:50]}"

    class Meta:
        verbose_name = "Лог платежа"
        verbose_name_plural = "Логи платежей"
