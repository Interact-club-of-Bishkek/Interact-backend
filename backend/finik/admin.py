# admin.py
from django.contrib import admin
from .models import Payment, PaymentLog, ProjectPayment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("payment_id", "first_name", "last_name", "amount", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("payment_id", "first_name", "last_name", "phone", "comment")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "level", "short_message")
    list_filter = ("level", "created_at")
    search_fields = ("message",)
    readonly_fields = ("created_at", "level", "message", "extra")
    ordering = ("-created_at",)

    def short_message(self, obj):
        return obj.message[:50] + ("..." if len(obj.message) > 50 else "")
    short_message.short_description = "Message"


@admin.register(ProjectPayment)
class ProjectPaymentAdmin(admin.ModelAdmin):
    list_display = ("payment_id", "project", "first_name", "last_name", "amount", "status", "created_at")
    list_filter = ("status", "project", "created_at")
    search_fields = ("payment_id", "first_name", "last_name", "phone", "comment", "project__name")
    readonly_fields = ("payment_id", "created_at", "payment_url")
    ordering = ("-created_at",)
