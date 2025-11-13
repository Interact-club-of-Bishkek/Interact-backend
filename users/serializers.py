from rest_framework import serializers
from .models import Volunteer, VolunteerApplication
from directions.models import VolunteerDirection  # добавляем для короткого сериализатора
from directions.serializers import VolunteerDirectionSerializer


# --------- Короткий сериализатор для направлений ---------
class VolunteerDirectionShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = VolunteerDirection
        fields = ['id', 'name']


# --------- Волонтёр ---------
class VolunteerSerializer(serializers.ModelSerializer):
    direction = VolunteerDirectionSerializer(many=True, read_only=True)

    class Meta:
        model = Volunteer
        fields = [
            'id', 'login', 'name', 'phone_number', 'email', 'image',
            'telegram_username', 'telegram_id', 'board', 'direction',
            'point', 'yellow_card'
        ]


# --------- Авторизация ---------
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


# --------- Заявки волонтёров ---------
class VolunteerApplicationSerializer(serializers.ModelSerializer):
    directions = VolunteerDirectionShortSerializer(many=True, read_only=True)  # короткий сериализатор!
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = VolunteerApplication
        fields = [
            'id', 'full_name', 'email', 'phone_number', 'photo', 'why_volunteer',
            'volunteer_experience', 'hobbies_skills', 'strengths', 'why_choose_you',
            'agree_inactivity_removal', 'agree_terms', 'ready_travel', 'ideas_improvements',
            'expectations', 'directions', 'weekly_hours', 'attend_meetings',
            'status', 'status_display', 'created_at', 'updated_at'
        ]


# --------- Обновление статуса ---------
class VolunteerApplicationStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VolunteerApplication
        fields = ['status']


# --------- Для отображения колонок ---------
class VolunteerColumnsSerializer(serializers.Serializer):
    submitted = VolunteerApplicationSerializer(many=True, read_only=True)
    interview = VolunteerApplicationSerializer(many=True, read_only=True)
    accepted = VolunteerSerializer(many=True, read_only=True)
