# directions/models.py
from django.db import models

class VolunteerDirection(models.Model):
    name = models.CharField(max_length=100, verbose_name="Направление для волонтёров")
    responsible = models.ForeignKey(
        'users.Volunteer', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Ответственный куратор",
        related_name="responsible_for_directions"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Направление волонтёров"
        verbose_name_plural = "Направления волонтёров"


class ProjectDirection(models.Model):
    name = models.CharField(max_length=100, verbose_name="Направление для проектов")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Направление проекта"
        verbose_name_plural = "Направления проектов"
