from django.contrib import admin
from django.utils.html import format_html
from users.models import VolunteerApplication, Volunteer, BotAccessConfig, VolunteerArchive

admin.site.register(VolunteerArchive)

@admin.register(VolunteerApplication)
class VolunteerApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone_number', 'status', 'photo_tag', 'created_at')
    list_filter = ('status', 'directions')
    search_fields = ('full_name', 'email', 'phone_number')
    # Добавлены поля в readonly_fields, чтобы их можно было включить в fieldsets
    readonly_fields = ('created_at', 'updated_at', 'photo_tag', 'volunteer_created') 

    fieldsets = (
        ('Личная информация', {
            'fields': (
                'full_name', 'email', 'phone_number', 'photo', 'photo_tag',
                'date_of_birth', 'place_of_study', 
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
            # Теперь volunteer_created можно включить, т.к. оно в readonly_fields
            'fields': ('status', 'volunteer', 'volunteer_created') 
        }),
    )

    def photo_tag(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="width: 100px; height:auto;" />', obj.photo.url)
        return "-"
    photo_tag.short_description = "Фото"

    def save_model(self, request, obj, form, change):
        creating_volunteer = False
        if obj.status == 'accepted' and not obj.volunteer_created:
            creating_volunteer = True

        super().save_model(request, obj, form, change)

        if creating_volunteer:
            volunteer = Volunteer.objects.create_user(
                name=obj.full_name,
                phone_number=obj.phone_number,
                email=obj.email
            )
            volunteer.direction.set(obj.directions.all())
            volunteer.save()
            
            obj.volunteer = volunteer
            obj.volunteer_created = True
            # Предотвращение рекурсии
            obj.save(update_fields=['volunteer', 'volunteer_created'])


@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('name', 'login', 'visible_password', 'phone_number', 'email', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'direction')
    search_fields = ('name', 'login', 'phone_number', 'email')
    readonly_fields = ('visible_password',)


@admin.register(BotAccessConfig)
class BotAccessConfigAdmin(admin.ModelAdmin):
    # Поля, которые будут видны в списке
    list_display = ('role', 'password')
    
    # Поля, которые можно редактировать прямо в списке
    list_editable = ('password',)
    
    # Ограничение: запрещаем создавать более двух записей (куратор и волонтер)
    def has_add_permission(self, request):
        if BotAccessConfig.objects.count() >= 2:
            return False
        return True

    # Запрещаем удалять записи, чтобы бот не "сломался"
    def has_delete_permission(self, request, obj=None):
        return False
