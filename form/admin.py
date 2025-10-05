from django.contrib import admin
from django.utils.html import format_html
from .models import VolunteerForm, VolunteerFormArchive, WaitingList, MailingPending, TextMailing


# 🔒 Только для чтения (архив и TextMailing)
class ReadOnlyAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        fields = [f.name for f in self.model._meta.fields]
        if 'image' in fields:
            fields.append('image_preview')
        return fields

    def image_preview(self, obj):
        if hasattr(obj, 'image') and obj.image:
            return format_html('<img src="{}" style="max-height:500px; max-width:500px;" />', obj.image.url)
        return "Нет фото"
    image_preview.short_description = 'Фото'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ✅ VolunteerForm — редактируемый, можно удалять
@admin.register(VolunteerForm)
class VolunteerFormAdmin(admin.ModelAdmin):
    list_display = ['name', 'id', 'phone_number', 'telegram_username', 'telegram_id', 'is_verified']
    search_fields = ['name', 'phone_number', 'telegram_username']
    list_filter = ['is_verified']
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:500px; max-width:500px;" />', obj.image.url)
        return "Нет фото"
    image_preview.short_description = 'Фото'


# 🔒 Архив
@admin.register(VolunteerFormArchive)
class VolunteerFormArchiveAdmin(ReadOnlyAdmin):
    list_display = ['name', 'id', 'moved_to', 'telegram_username', 'telegram_id']
    search_fields = ['name', 'moved_to', 'telegram_username']
    list_filter = ['moved_to']


# ✅ Ожидание — можно редактировать и удалять
@admin.register(WaitingList)
class WaitingListAdmin(admin.ModelAdmin):
    list_display = ['name', 'id', 'is_approved', 'telegram_username', 'telegram_id']
    search_fields = ['name', 'phone_number', 'telegram_username']
    list_filter = ['is_approved']
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:500px; max-width:500px;" />', obj.image.url)
        return "Нет фото"
    image_preview.short_description = 'Фото'


# ✅ MailingPending — можно редактировать и удалять
@admin.register(MailingPending)
class MailingPendingAdmin(admin.ModelAdmin):
    list_display = ['name', 'id', 'telegram_username', 'telegram_id']
    search_fields = ['name', 'telegram_username']
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:500px; max-width:500px;" />', obj.image.url)
        return "Нет фото"
    image_preview.short_description = 'Фото'


# 🔒 TextMailing — только чтение
@admin.register(TextMailing)
class TextMailingAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False
