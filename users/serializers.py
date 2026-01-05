from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import Volunteer, VolunteerApplication, VolunteerArchive
from directions.models import VolunteerDirection 

# --------- Сериализатор для Направлений ---------
class VolunteerDirectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VolunteerDirection
        fields = ['id', 'name']


# --------- Сериализатор Волонтёра (User) ---------
class VolunteerSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)
    # Используем правильное имя сериализатора
    direction = VolunteerDirectionSerializer(many=True, read_only=True)

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


# --------- Сериализатор Заявки (ИСПРАВЛЕННЫЙ) ---------
class VolunteerApplicationSerializer(serializers.ModelSerializer):
    # Поле для записи (принимает ID)
    directions = serializers.PrimaryKeyRelatedField(
        queryset=VolunteerDirection.objects.all(), 
        many=True
    )

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    photo_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = VolunteerApplication
        fields = '__all__' # Можно использовать all для краткости, или перечислить поля как у вас
        read_only_fields = ('photo_url', 'status_display', 'created_at', 'updated_at')

    # !!! ГЛАВНОЕ ИСПРАВЛЕНИЕ !!!
    # Этот метод подменяет ID на полные объекты при отправке данных на фронт
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Заменяем список ID на список объектов {id, name}
        representation['directions'] = VolunteerDirectionSerializer(instance.directions.all(), many=True).data
        return representation

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


# --------- Для отображения колонок ---------
class VolunteerColumnsSerializer(serializers.Serializer):
    # Используем ApplicationSerializer везде, чтобы данные были одинаковыми
    submitted = VolunteerApplicationSerializer(many=True, read_only=True)
    interview = VolunteerApplicationSerializer(many=True, read_only=True)
    accepted = VolunteerApplicationSerializer(many=True, read_only=True)


class BotAuthSerializer(serializers.Serializer):
    access_type = serializers.ChoiceField(choices=['commands', 'add_project'])
    password = serializers.CharField()