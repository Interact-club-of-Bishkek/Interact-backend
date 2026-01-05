from rest_framework import serializers
from .models import Project, YearResult
from directions.models import ProjectDirection
from django.utils import timezone

class ProjectSerializer(serializers.ModelSerializer):
    # Указываем направление только для чтения (для отображения на фронте/в боте)
    direction_detail = serializers.SerializerMethodField() 

    # Позволяет передавать direction_id при POST (для записи)
    direction_id = serializers.PrimaryKeyRelatedField(
        queryset=ProjectDirection.objects.all(),
        source='direction',
        write_only=True,
        required=False,
    )

    time_start = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    time_end = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S") # Исправлено :S на :%S
    date = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            'id', 'image', 'name', 'title', 'price', 'category',
            'time_start', 'time_end',
            'direction_detail', 'direction_id',
            'phone_number', 'address',
            'date'
        )
        ref_name = 'ProjectsProjectSerializer'

    def get_date(self, obj):
        return obj.created_at.date() if obj.created_at else None
    
    def get_direction_detail(self, obj):
        # Чтобы избежать рекурсии, просто возвращаем ID и имя направления
        if obj.direction:
            return {"id": obj.direction.id, "name": obj.direction.name}
        return None

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

class DirectionSerializer(serializers.ModelSerializer):
    projects = serializers.SerializerMethodField()

    class Meta:
        model = ProjectDirection
        fields = ('id', 'name', 'projects')
        ref_name = 'ProjectsDirectionSerializer'

    def get_projects(self, obj):
        now = timezone.now()
        # ИСПРАВЛЕНО: order_only -> order_by
        active_projects = obj.projects.filter(is_archived=False).order_by('time_start')
        return ProjectSerializer(active_projects, many=True).data

class YearResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = YearResult
        fields = '__all__'