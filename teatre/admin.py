from django.contrib import admin
from .models import Booking
from django.utils.html import format_html

class FullNameFilter(admin.SimpleListFilter):
    title = 'ФИО'
    parameter_name = 'full_name'
    def lookups(self, request, model_admin):
        names = set([b.full_name for b in model_admin.model.objects.all()])
        return [(name, name) for name in names]
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(full_name=self.value())
        return queryset

class PhoneFilter(admin.SimpleListFilter):
    title = 'Телефон'
    parameter_name = 'phone'
    def lookups(self, request, model_admin):
        phones = set([b.phone for b in model_admin.model.objects.all()])
        return [(p, p) for p in phones]
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(phone=self.value())
        return queryset

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "hall_type", "row", "seat", "price", "created_at", "download_ticket")
    list_filter = (FullNameFilter, PhoneFilter, "hall_type", "row", "seat")
    search_fields = ("full_name", "phone")

    def download_ticket(self, obj):
        if obj.ticket_pdf:
            return format_html('<a href="{}" target="_blank">Скачать билет</a>', obj.ticket_pdf.url)
        return "Билет не создан"
    download_ticket.short_description = "Билет PDF"
