from django.contrib import admin
from django.utils.html import format_html
from .models import Project, YearResult

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "category_verbose", "direction", "price", "date", "image_tag")
    list_filter = ("category", "direction")
    search_fields = ("name", "title")
    ordering = ("-date",)
    fieldsets = (
        ("Основная информация", {
            "fields": ("name", "title", "image", "direction", "category", "price", "date")
        }),
    )
    save_on_top = True

    # Красивое отображение категории на русском
    def category_verbose(self, obj):
        return dict(obj.CATEGORY_CHOICES).get(obj.category, obj.category)
    category_verbose.short_description = "Категория"

    # Превью изображения
    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 100px; height:auto;" />', obj.image.url)
        return "-"
    image_tag.short_description = "Обложка"


@admin.register(YearResult)
class YearResultAdmin(admin.ModelAdmin):
    list_display = ("sport", "cyber_sport", "education", "fundraising", "cultural", "total_amount")
    readonly_fields = ("total_amount",)  # Общая сумма вычисляется автоматически, редактировать не нужно
    fieldsets = (
        ("Результаты года", {
            "fields": ("sport", "cyber_sport", "education", "fundraising", "cultural", "total_amount")
        }),
    )
    ordering = ("-id",)
