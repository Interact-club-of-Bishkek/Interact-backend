from django.db import models

class Booking(models.Model):
    full_name = models.CharField(
        max_length=255, 
        verbose_name="ФИО"
    )
    phone = models.CharField(
        max_length=20, 
        verbose_name="Телефон"
    )
    row = models.PositiveIntegerField(
        verbose_name="Ряд"
    )
    seat = models.PositiveIntegerField(
        verbose_name="Место"
    )
    price = models.PositiveIntegerField(
        default=1000, 
        verbose_name="Цена"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Дата бронирования"
    )
    ticket_pdf = models.FileField(
        upload_to='media/tickets/', 
        verbose_name="Билет PDF",
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"
        ordering = ["row", "seat"]

    def __str__(self):
        return f"Ряд {self.row}, Место {self.seat} — {self.full_name}"
