from django.contrib import admin
from django.utils.html import format_html
from users.models import VolunteerApplication, Volunteer, BotAccessConfig, VolunteerArchive

@admin.register(VolunteerArchive)
class VolunteerArchiveAdmin(admin.ModelAdmin):
    # Добавили фото в список архива
    list_display = ('full_name', 'email', 'photo_tag', 'created_at')
    readonly_fields = ('photo_tag',)

    def photo_tag(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="width: 70px; border-radius: 5px;" />', obj.photo.url)
        return "Нет фото"
    photo_tag.short_description = "Предпросмотр фото"


@admin.register(VolunteerApplication)
class VolunteerApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone_number', 'status', 'photo_tag', 'created_at')
    list_filter = ('status', 'direction')
    search_fields = ('full_name', 'email', 'phone_number')
    readonly_fields = ('created_at', 'updated_at', 'photo_tag', 'volunteer_created') 

    fieldsets = (
        ('Личная информация', {
            'fields': (
                'full_name', 'email', 'phone_number', 'photo', 'photo_tag',
                'date_of_birth', 'place_of_study', 
            )
        }),
        ('Структура', { 'fields': ('direction', 'commands') }),
        ('Анкетные вопросы', {
            'fields': (
                'why_volunteer', 'volunteer_experience', 'hobbies_skills', 'strengths',
                'why_choose_you', 'choice_motives', 
                'agree_inactivity_removal', 'agree_terms', 'ready_travel',
                'ideas_improvements', 'expectations', 'weekly_hours', 'attend_meetings'
            )
        }),
        ('Статус', { 'fields': ('status', 'volunteer', 'volunteer_created') }),
    )

    def photo_tag(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="width: 100px; height:auto; border-radius: 10px;" />', obj.photo.url)
        return "-"
    photo_tag.short_description = "Фото"

    def save_model(self, request, obj, form, change):
        creating_volunteer = False
        if obj.status == 'accepted' and not obj.volunteer_created:
            creating_volunteer = True

        super().save_model(request, obj, form, change)

        if creating_volunteer:
            # Создаем волонтера
            volunteer = Volunteer.objects.create_user(
                login=obj.email if obj.email else None,
                name=obj.full_name,
                phone_number=obj.phone_number,
                email=obj.email
            )
            
            if obj.direction:
                volunteer.direction.add(obj.direction)
            if obj.commands.exists():
                volunteer.commands.set(obj.commands.all())
                
            # Важно: переносим фото из анкеты в профиль волонтера
            if obj.photo:
                volunteer.image = obj.photo
                
            volunteer.save()
            
            obj.volunteer = volunteer
            obj.volunteer_created = True
            obj.save(update_fields=['volunteer', 'volunteer_created'])


@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    # Добавили image_tag в список волонтеров
    list_display = ('image_tag', 'name', 'login', 'visible_password', 'role', 'point', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active', 'direction')
    search_fields = ('name', 'login', 'phone_number', 'email')
    readonly_fields = ('visible_password', 'is_staff', 'image_tag')

    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 50%;" />', obj.image.url)
        return "Нет фото"
    image_tag.short_description = "Аватар"

@admin.register(BotAccessConfig)
class BotAccessConfigAdmin(admin.ModelAdmin):
    list_display = ('role', 'password')
    list_editable = ('password',)
