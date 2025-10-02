from django.db import models

class Payment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Ожидает оплаты"),
        ("success", "Успешно"),
        ("failed", "Неудачно"),
    ]
    payment_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма")
    comment = models.CharField(max_length=255, blank=True, null=True, verbose_name="Комментарий")
    first_name = models.CharField(max_length=100, verbose_name="Имя")
    last_name = models.CharField(max_length=100, verbose_name="Фамилия")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.amount} сом ({self.status})"


class PaymentLog(models.Model):
    LEVEL_CHOICES = (
        ("INFO", "Info"),
        ("WARNING", "Warning"),
        ("ERROR", "Error"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    message = models.TextField()
    extra = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"[{self.created_at}] {self.level}: {self.message[:50]}"