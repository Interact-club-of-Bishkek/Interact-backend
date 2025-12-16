from rest_framework import serializers
from .models import Volunteer, VolunteerApplication
from directions.models import VolunteerDirection 
# assuming you have this serializer file
# from directions.serializers import VolunteerDirectionSerializer 


# --------- Короткий сериализатор для направлений ---------
class VolunteerDirectionShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = VolunteerDirection
        fields = ['id', 'name']


# --------- Волонтёр (Исправлено: URL фото) ---------
class VolunteerSerializer(serializers.ModelSerializer):
    # Используем SerializerMethodField для фото, чтобы вернуть полный URL
    image_url = serializers.SerializerMethodField(read_only=True)
    direction = VolunteerDirectionShortSerializer(many=True, read_only=True)

    class Meta:
        model = Volunteer
        fields = [
            'id', 'login', 'name', 'phone_number', 'email', 'image_url', # ИЗМЕНЕНО: image -> image_url
            'telegram_username', 'telegram_id', 'board', 'direction',
            'point', 'yellow_card'
        ]

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


# --------- Авторизация (Без изменений) ---------
class VolunteerLoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField(write_only=True)
    volunteer = serializers.HiddenField(default=None)

    def validate(self, attrs):
        login = attrs.get('login')
        password = attrs.get('password')
        from django.contrib.auth import authenticate
        volunteer = authenticate(login=login, password=password)
        if not volunteer:
            raise serializers.ValidationError("Неправильный логин или пароль")
        attrs['volunteer'] = volunteer
        return attrs


# --------- Заявки волонтёров (Исправлено: URL фото и поля анкеты) ---------
# --------- Заявки волонтёров (Исправлено: URL фото и поля анкеты) ---------
class VolunteerApplicationSerializer(serializers.ModelSerializer):
    
    # 1. ЧТЕНИЕ: красиво выводим направления
    directions_display = VolunteerDirectionShortSerializer(source='directions', many=True, read_only=True) 
    
    # 2. ЗАПИСЬ: принимаем список ID от бота
    directions = serializers.PrimaryKeyRelatedField(
        queryset=VolunteerDirection.objects.all(), 
        many=True, 
        write_only=True
    )

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    photo_url = serializers.SerializerMethodField(read_only=True) # Чтение: полный URL фото

    class Meta:
        model = VolunteerApplication
        fields = [
            'id', 'full_name', 'email', 'phone_number', 'photo_url', 
            
            'date_of_birth', 'place_of_study', 'choice_motives',
            
            'why_volunteer', 'volunteer_experience', 'hobbies_skills', 'strengths',
            'why_choose_you', 'agree_inactivity_removal', 'agree_terms', 'ready_travel',
            'ideas_improvements', 'expectations', 
            
            'directions', # <-- Используется для записи (список ID)
            'directions_display', # <-- Используется для чтения (объекты)
            
            'weekly_hours', 'attend_meetings',
            
            'feedback',
            
            'status', 'status_display', 'created_at', 'updated_at'
        ]
        
        read_only_fields = ('photo_url', 'status_display', 'created_at', 'updated_at')
# ...
        # Убедимся, что directions не будет использоваться для записи, 
        # если используется его read_only представление (VolunteerDirectionShortSerializer)
        # Если API принимает 'directions' как список ID, то нужно 
        # исключить поле с read_only сериализатором из полей для записи
        read_only_fields = ('photo_url', 'status_display', 'created_at', 'updated_at')

    def get_photo_url(self, obj):
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None

# --------- Обновление статуса (Без изменений) ---------
class VolunteerApplicationStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VolunteerApplication
        fields = ['status']


# --------- Для отображения колонок (Без изменений) ---------
class VolunteerColumnsSerializer(serializers.Serializer):
    submitted = VolunteerApplicationSerializer(many=True, read_only=True)
    interview = VolunteerApplicationSerializer(many=True, read_only=True)
    accepted = VolunteerSerializer(many=True, read_only=True)