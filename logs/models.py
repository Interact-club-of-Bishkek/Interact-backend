from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ActionLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Пользователь")
    action = models.CharField(max_length=255, verbose_name="Действие")
    model_name = models.CharField(max_length=255, verbose_name="Модель")
    object_id = models.PositiveIntegerField(null=True, verbose_name="ID объекта")
    changes = models.TextField(null=True, blank=True, verbose_name="Изменения")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Время")

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Лог действия"
        verbose_name_plural = "Логи действий"

    def __str__(self):
        return f"{self.timestamp} — {self.user} — {self.action}"
