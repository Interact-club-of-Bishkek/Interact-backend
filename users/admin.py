from django.contrib import admin
from django.utils.html import format_html
from users.models import VolunteerApplication, Volunteer

@admin.register(VolunteerApplication)
class VolunteerApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone_number', 'status', 'photo_tag', 'created_at')
    list_filter = ('status', 'directions')
    search_fields = ('full_name', 'email', 'phone_number')
    # Добавляем updated_at и volunteer_created в readonly_fields, если они нужны для просмотра
    readonly_fields = ('created_at', 'updated_at', 'photo_tag', 'volunteer_created') 

    fieldsets = (
        ('Личная информация', {
            'fields': (
                'full_name', 'email', 'phone_number', 'photo', 'photo_tag',
                'date_of_birth', 'place_of_study', # Добавленные поля
            )
        }),
        ('Анкетные вопросы', {
            'fields': (
                'why_volunteer', 'volunteer_experience', 'hobbies_skills', 'strengths',
                'why_choose_you', 'choice_motives', 
                'agree_inactivity_removal', 'agree_terms', 'ready_travel',
                'ideas_improvements', 'expectations', 'directions', 'weekly_hours', 'attend_meetings'
            )
        }),
        ('Статус', {
            # ИСПРАВЛЕНО: УДАЛЕНО 'volunteer_created' из полей для редактирования (так как editable=False)
            'fields': ('status', 'volunteer', 'volunteer_created') 
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def photo_tag(self, obj):
        if obj.photo:
            # Убеждаемся, что здесь используется obj.photo.url, который должен быть корректно настроен
            return format_html('<img src="{}" style="width: 100px; height:auto;" />', obj.photo.url)
        return "-"
    photo_tag.short_description = "Фото"

    def save_model(self, request, obj, form, change):
        creating_volunteer = False
        if obj.status == 'accepted' and not obj.volunteer_created:
            creating_volunteer = True

        # Важно: Сначала сохраняем Application, чтобы получить его PK
        super().save_model(request, obj, form, change)

        if creating_volunteer:
            # Создаем волонтера
            volunteer = Volunteer.objects.create_user(
                name=obj.full_name,
                phone_number=obj.phone_number,
                email=obj.email
            )
            # Устанавливаем направления
            volunteer.direction.set(obj.directions.all())
            volunteer.save()
            
            # Обновляем Application ссылкой на созданного Volunteer и флаг
            obj.volunteer = volunteer
            obj.volunteer_created = True
            # Используем save(update_fields=...) для предотвращения рекурсии
            obj.save(update_fields=['volunteer', 'volunteer_created'])


@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('name', 'login', 'visible_password', 'phone_number', 'email', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'direction')
    search_fields = ('name', 'login', 'phone_number', 'email')
    readonly_fields = ('visible_password',)