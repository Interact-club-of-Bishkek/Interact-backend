from rest_framework import serializers
from django.contrib.auth import authenticate
# Импортируем модели из вашего проекта
# Убедитесь, что пути импорта (например, .models) верны для вашей структуры папок
from .models import Volunteer, VolunteerApplication, VolunteerArchive
from directions.models import VolunteerDirection 

# --------- Сериализатор для Направлений (короткий, для вложенности) ---------
class VolunteerDirectionShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = VolunteerDirection
        fields = ['id', 'name']


# --------- Сериализатор Волонтёра (User) ---------
class VolunteerSerializer(serializers.ModelSerializer):
    # Поле только для чтения, возвращает полный URL картинки
    image_url = serializers.SerializerMethodField(read_only=True)
    # Вложенный сериализатор для отображения направлений
    direction = VolunteerDirectionShortSerializer(many=True, read_only=True)

    class Meta:
        model = Volunteer
        fields = [
            'id', 'login', 'name', 'phone_number', 'email', 'image_url',
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


# --------- Сериализатор Авторизации ---------
class VolunteerLoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField(write_only=True)
    volunteer = serializers.HiddenField(default=None)

    def validate(self, attrs):
        login = attrs.get('login')
        password = attrs.get('password')
        volunteer = authenticate(login=login, password=password)
        if not volunteer:
            raise serializers.ValidationError("Неправильный логин или пароль")
        attrs['volunteer'] = volunteer
        return attrs


# --------- Сериализатор Заявки (ГЛАВНОЕ ИСПРАВЛЕНИЕ) ---------
class VolunteerApplicationSerializer(serializers.ModelSerializer):
    
    # 1. Поле для ЧТЕНИЯ (вывод названий направлений для админки/фронта)
    # Использует 'source', чтобы брать данные из поля directions модели
    directions_details = VolunteerDirectionShortSerializer(source='directions', many=True, read_only=True)
    
    # 2. Поле для ЗАПИСИ (принимает список ID: [1, 2])
    # Обязательно должно называться 'directions', как в модели!
    directions = serializers.PrimaryKeyRelatedField(
        queryset=VolunteerDirection.objects.all(), 
        many=True
    )

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    photo_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = VolunteerApplication
        fields = [
            'id', 
            # Личные данные
            'full_name', 'email', 'phone_number', 
            
            # === ВАЖНО: Поле для ЗАГРУЗКИ фото ===
            'photo',      # Это поле принимает файл (write)
            'photo_url',  # Это поле возвращает ссылку (read)
            # =====================================
            
            'date_of_birth', 'place_of_study', 'choice_motives',
            
            # Анкетные данные
            'why_volunteer', 'volunteer_experience', 'hobbies_skills', 'strengths',
            'why_choose_you', 'agree_inactivity_removal', 'agree_terms', 'ready_travel',
            'ideas_improvements', 'expectations', 
            
            # Направления
            'directions',          # <-- Сюда бот пишет ID
            'directions_details',  # <-- Отсюда читаем названия
            
            # Организационные вопросы
            'weekly_hours', 'attend_meetings', 'feedback',
            
            # Системные поля
            'status', 'status_display', 'created_at', 'updated_at'
        ]
        
        # Поля, которые нельзя изменять вручную через API
        read_only_fields = ('photo_url', 'status_display', 'created_at', 'updated_at', 'directions_details')

    def get_photo_url(self, obj):
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None


# --------- Обновление статуса ---------
class VolunteerApplicationStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VolunteerApplication
        fields = ['status']


# --------- Для отображения колонок (Kanban) ---------
class VolunteerColumnsSerializer(serializers.Serializer):
    submitted = VolunteerApplicationSerializer(many=True, read_only=True)
    interview = VolunteerApplicationSerializer(many=True, read_only=True)
    accepted = VolunteerSerializer(many=True, read_only=True)