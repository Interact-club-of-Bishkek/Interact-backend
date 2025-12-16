from rest_framework import serializers
from .models import Project, YearResult
from directions.models import ProjectDirection
from django.utils import timezone


# ----------------------------------------------------------------------
# ПЕРЕНОСИМ ProjectSerializer В НАЧАЛО, ЧТОБЫ DirectionSerializer МОГ НА НЕГО ССЫЛАТЬСЯ
# А ДЛЯ ОБРАТНОЙ ССЫЛКИ ИСПОЛЬЗУЕМ СТРОКУ
# ----------------------------------------------------------------------

# ВАЖНО: Определяем ProjectSerializer первым, но убираем прямое использование DirectionSerializer
class ProjectSerializer(serializers.ModelSerializer):
    # ИСПРАВЛЕНО: Заменяем прямое использование DirectionSerializer на строковое имя
    direction = serializers.SerializerMethodField() 

    # Позволяет передавать direction_id при POST/PUT
    direction_id = serializers.PrimaryKeyRelatedField(
        queryset=ProjectDirection.objects.all(),
        source='direction',
        write_only=True,
        required=False,
    )

    time_start = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    time_end = serializers.DateTimeField(format="%Y-%m-%d %H:%M:S")

    # Только дата создания
    date = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            'id', 'image', 'name', 'title', 'price',
            'time_start', 'time_end',
            'direction', 'direction_id',
            'phone_number', 'address',
            'date'
        )

    def get_date(self, obj):
        if obj.created_at:
            return obj.created_at.date()
        return None
    
    # НОВЫЙ МЕТОД: Для получения Direction, чтобы избежать рекурсии
    def get_direction(self, obj):
        # Используем DirectionSerializer здесь, когда он уже определен ниже
        from . import serializers as current_serializers
        return current_serializers.DirectionSerializer(obj.direction).data if obj.direction else None


    def validate_phone_number(self, value):
        cleaned = value.replace('+', '').replace('-', '').replace(' ', '')
        if not cleaned.isdigit():
            raise serializers.ValidationError("Неверный формат номера телефона.")
        return value

    def validate(self, data):
        time_start = data.get('time_start')
        time_end = data.get('time_end')

        if time_start and time_end and time_start >= time_end:
            raise serializers.ValidationError({
                "time_end": "Время окончания должно быть позже времени начала."
            })

        return data


# Оставляем DirectionSerializer как есть, но он теперь ссылается на ProjectSerializer, 
# который определен выше.
class DirectionSerializer(serializers.ModelSerializer):
    projects = serializers.SerializerMethodField()

    class Meta:
        model = ProjectDirection
        fields = ('id', 'name', 'projects')
        ref_name = 'ProjectsDirectionSerializer'

    def get_projects(self, obj):
        now = timezone.now()
        # Автоархивируем прямо здесь
        Project.objects.filter(time_end__lt=now, is_archived=False).update(is_archived=True)
        # Фильтруем только активные проекты
        active_projects = obj.projects.filter(is_archived=False).order_only('time_start')
        # ProjectSerializer уже определен
        return ProjectSerializer(active_projects, many=True).data


class YearResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = YearResult
        fields = '__all__'