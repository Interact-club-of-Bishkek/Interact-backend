from django.contrib import admin
from django.utils.html import format_html
from .models import Project, YearResult


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "category_verbose", "direction", "price", "time_start", "image_tag", "address")
    list_filter = ("category", "direction")
    search_fields = ("name", "title", "address", "phone_number")
    ordering = ("-time_start",)
    save_on_top = True

    fieldsets = (
        ("Основная информация", {
            "fields": (
                "name", "title", "image", "direction", "category", "price",
                "time_start", "time_end", "phone_number", "address"
            )
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)  # правильно, request передается

    def category_verbose(self, obj):
        return dict(obj.CATEGORY_CHOICES).get(obj.category, obj.category)
    category_verbose.short_description = "Категория"

    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 100px; height:auto;"/>', obj.image.url)
        return "-"
    image_tag.short_description = "Обложка"


@admin.register(YearResult)
class YearResultAdmin(admin.ModelAdmin):
    list_display = ("sport", "cyber_sport", "education", "fundraising", "cultural", "total_amount")
    readonly_fields = ("total_amount",)
    ordering = ("-id",)

    fieldsets = (
        ("Результаты года", {
            "fields": ("sport", "cyber_sport", "education", "fundraising", "cultural", "total_amount")
        }),
    )

    # Автоматический расчёт total_amount при сохранении
    def save_model(self, request, obj, form, change):
        obj.total_amount = sum([
            obj.sport,
            obj.cyber_sport,
            obj.education,
            obj.fundraising,
            obj.cultural
        ])
        super().save_model(request, obj, form, change)
