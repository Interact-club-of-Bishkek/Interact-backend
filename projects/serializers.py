from rest_framework import serializers
from .models import Project, YearResult
from directions.models import ProjectDirection


class DirectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectDirection
        fields = ('id', 'name')  # добавил id для удобства
        ref_name = 'ProjectsDirectionSerializer'


class YearResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = YearResult
        fields = '__all__'


class ProjectSerializer(serializers.ModelSerializer):
    # Nested serializer для чтения
    direction = DirectionSerializer(read_only=True)
    # Поле для записи через id
    direction_id = serializers.PrimaryKeyRelatedField(
        queryset=ProjectDirection.objects.all(),
        source='direction',
        write_only=True,
        required=False,  # можно оставить пустым
    )

    # Явные форматы даты и времени
    date = serializers.DateField(format="%Y-%m-%d")
    time_start = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    time_end = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")

    class Meta:
        model = Project
        fields = (
            'id', 'image', 'name', 'title', 'price',
            'time_start', 'time_end', 'direction', 'direction_id',
            'phone_number', 'address', 'date'
        )

    # Валидация номера телефона
    def validate_phone_number(self, value):
        cleaned = value.replace('+', '').replace('-', '').replace(' ', '')
        if not cleaned.isdigit():
            raise serializers.ValidationError("Неверный формат номера")
        return value

    # Дополнительно можно добавить валидацию времени
    def validate(self, data):
        time_start = data.get('time_start')
        time_end = data.get('time_end')
        if time_start and time_end and time_start >= time_end:
            raise serializers.ValidationError({
                "time_end": "Время конца должно быть позже времени начала."
            })
        return data
