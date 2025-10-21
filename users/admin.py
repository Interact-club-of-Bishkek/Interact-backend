from django.contrib import admin
from .models import Volunteer, Direction

@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ['name', 'login', 'visible_password','telegram_username', 'phone_number', 'point', 'yellow_card']
    readonly_fields = ['login', 'visible_password', 'telegram_id']  # чтоб показывать, но не редактировать

    # Вот здесь явно указываешь поля, которые показываются при редактировании/создании
    fields = (
        'login',           # будет readonly из-за readonly_fields
        'visible_password', # будет readonly
        'name',
        'phone_number',
        'image',
        'telegram_username',
        'telegram_id',
        'direction',
        'board',
        'point',
        'yellow_card',
    )

@admin.register(Direction)
class DirectionAdmin(admin.ModelAdmin):
    list_display = ['name']
