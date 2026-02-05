from django.contrib import admin
from django.utils.html import format_html
from users.models import VolunteerApplication, Volunteer, BotAccessConfig, VolunteerArchive

admin.site.register(VolunteerArchive)

@admin.register(VolunteerApplication)
class VolunteerApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone_number', 'status', 'photo_tag', 'created_at')
    # ИСПРАВЛЕНИЕ 1: directions -> direction
    list_filter = ('status', 'direction')
    search_fields = ('full_name', 'email', 'phone_number')
    readonly_fields = ('created_at', 'updated_at', 'photo_tag', 'volunteer_created')

    fieldsets = (
        ('Учетные данные', {
            'fields': ('login', 'visible_password', 'role', 'is_active')
        }),
        ('Личные данные', {
            'fields': ('name', 'phone_number', 'email', 'image')
        }),
        ('Структура', {
            'fields': ('direction', 'commands')
        }),
        ('Анкетные вопросы', {
            'fields': (
                'why_volunteer', 'volunteer_experience', 'hobbies_skills', 'strengths',
                'why_choose_you', 'choice_motives',
                'agree_inactivity_removal', 'agree_terms', 'ready_travel',
                # ИСПРАВЛЕНИЕ 2: directions -> direction
                'ideas_improvements', 'expectations', 'direction', 'weekly_hours', 'attend_meetings'
            )
        }),
        ('Статус', {
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
            # ИСПРАВЛЕНИЕ 3: obj.directions -> obj.direction
            # Проверяем, есть ли вообще такое поле у объекта перед обращением
            if hasattr(obj, 'direction'):
                volunteer.direction.set(obj.direction.all())
            
            volunteer.save()
            
            obj.volunteer = volunteer
            obj.volunteer_created = True
            obj.save(update_fields=['volunteer', 'volunteer_created'])


@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('name', 'login', 'visible_password', 'phone_number', 'email', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'direction')
    search_fields = ('name', 'login', 'phone_number', 'email')
    readonly_fields = ('visible_password',)


@admin.register(BotAccessConfig)
class BotAccessConfigAdmin(admin.ModelAdmin):
    list_display = ('role', 'password')
    list_editable = ('password',)
    
    def has_add_permission(self, request):
        if BotAccessConfig.objects.count() >= 2:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        return False