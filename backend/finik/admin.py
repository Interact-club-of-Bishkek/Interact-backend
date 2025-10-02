# payments/admin.py
from django.contrib import admin
from .models import Payment, PaymentLog


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "first_name", "last_name", "phone", "amount", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("first_name", "last_name", "phone", "comment")


@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "level", "message")
    list_filter = ("level", "created_at")
    search_fields = ("message",)