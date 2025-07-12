from rest_framework import serializers
from .models import Direction, Volunteer
from django.contrib.auth.hashers import check_password


class VolunteerNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Volunteer
        fields = ['name']


class DirectionSerializer(serializers.ModelSerializer):
    volunteers = VolunteerNameSerializer(many=True, read_only=True)

    class Meta:
        model = Direction
        fields = ['name', 'volunteers']


class VolunteerSerializer(serializers.ModelSerializer):
    direction = serializers.StringRelatedField(many=True)

    class Meta:
        model = Volunteer
        fields = ['name', 'phone_number', 'image', 'telegram_username', 'direction', 'board', 'point', 'yellow_card']


class VolunteerLoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        login = data.get("login")
        password = data.get("password")

        try:
            volunteer = Volunteer.objects.get(login__iexact=login)
        except Volunteer.DoesNotExist:
            raise serializers.ValidationError("Пользователь не найден")

        if not volunteer.check_password(password):
            raise serializers.ValidationError("Неверный пароль")

        if not volunteer.board:
            raise serializers.ValidationError("Нет доступа. У вас нет разрешения на вход")

        data["volunteer"] = volunteer
        return data