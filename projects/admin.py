from django.contrib import admin
from django.utils.html import format_html
from .models import FAQ, Partner, Project, TeamMember, YearResult, HeroSlide
from django.utils import timezone

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "category_verbose", "direction", "price", "time_start", "time_end", "image_tag", "is_archived")
    list_filter = ("category", "direction", "is_archived")
    search_fields = ("name", "title", "address", "phone_number")
    ordering = ("-time_start",)
    save_on_top = True

    fieldsets = (
        ("Основная информация", {
            "fields": (
                "name", "title", "image", "direction", "category", "price",
                "time_start", "time_end", "phone_number", "address", "is_archived"
            )
        }),
    )

    def category_verbose(self, obj):
        return dict(obj.CATEGORY_CHOICES).get(obj.category, obj.category)
    category_verbose.short_description = "Категория"

    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 100px; height:auto;"/>', obj.image.url)
        return "-"
    image_tag.short_description = "Обложка"

    # Авто-архивирование при сохранении
    def save_model(self, request, obj, form, change):
        if obj.time_end and obj.time_end < timezone.now():
            obj.is_archived = True
        super().save_model(request, obj, form, change)


@admin.register(YearResult)
class YearResultAdmin(admin.ModelAdmin):
    list_display = ("sport", "cyber_sport", "education", "fundraising", "cultural", "total_amount")
    ordering = ("-id",)

    fieldsets = (
        ("Результаты года", {
            "fields": ("sport", "cyber_sport", "education", "fundraising", "cultural", "total_amount")
        }),
    )

@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('name',)

@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ('title', 'badge', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    search_fields = ('title', 'description')

@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'position', 'order', 'is_active')
    list_editable = ('order', 'is_active')

admin.site.register(FAQ)
