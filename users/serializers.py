from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import Attendance, Volunteer, VolunteerApplication, ActivityTask, ActivitySubmission
from directions.models import VolunteerDirection
from commands.models import Command
from commands.serializers import QuestionSerializer

# --- Регистрация ---
class VolunteerRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Volunteer
        fields = ['login', 'password']

    def create(self, validated_data):
        return Volunteer.objects.create_user(**validated_data)

# --- Справочники ---
class VolunteerDirectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VolunteerDirection
        fields = ['id', 'name']

class CommandSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Command
        fields = ['id', 'title', 'slug', 'leader', 'direction', 'questions']

class VolunteerSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)
    direction = VolunteerDirectionSerializer(many=True, read_only=True)
    commands = CommandSerializer(source='volunteer_commands', many=True, read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    is_team_leader = serializers.SerializerMethodField()
    
    # 🔥 1. Поле для количества карточек
    yellow_card_count = serializers.SerializerMethodField()

    class Meta:
        model = Volunteer
        fields = [
            'id', 'login', 'name', 'phone_number', 'email', 
            'image', 'image_url', 
            'role', 'role_display', 'direction', 'commands', 
            'point', 
            'yellow_card_count', # 🔥 2. Обязательно добавляем в список полей
            'is_team_leader'
        ]
        read_only_fields = ['point', 'role', 'login', 'yellow_card_count']

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None

    def get_is_team_leader(self, obj):
        return Command.objects.filter(leader=obj).exists()

    # 🔥 3. Считаем через related_name из models.py
    def get_yellow_card_count(self, obj):
        # Благодаря related_name='yellow_cards' в модели YellowCard
        return obj.yellow_cards.count()
    
    
# --- Задачи (для баллов) ---
class ActivityTaskSerializer(serializers.ModelSerializer):
    command_name = serializers.CharField(source='command.title', read_only=True, default=None)
    command_id = serializers.IntegerField(source='command.id', read_only=True, default=None)
    title_en = serializers.CharField(read_only=True)
    direction_id = serializers.SerializerMethodField()

    class Meta:
        model = ActivityTask
        fields = [
            'id', 'title', 'title_en', 'points', 
            'is_flexible', 'command_id', 'command_name', 'direction_id'
        ]

    def get_direction_id(self, obj):
        if obj.command and obj.command.direction:
            return obj.command.direction.id
        return None

class ActivitySubmissionSerializer(serializers.ModelSerializer):
    task_details = ActivityTaskSerializer(source='task', read_only=True)
    volunteer_name = serializers.ReadOnlyField(source='volunteer.name')
    volunteer_id = serializers.IntegerField(read_only=True)
    
    # 🔥 ЯВНО указываем, что эти поля принимают ID (для записи)
    command = serializers.PrimaryKeyRelatedField(
        queryset=Command.objects.all(), 
        required=False, 
        allow_null=True
    )
    direction = serializers.PrimaryKeyRelatedField(
        queryset=VolunteerDirection.objects.all(), 
        required=False, 
        allow_null=True
    )

    command_title = serializers.ReadOnlyField(source='command.title')
    direction_name = serializers.ReadOnlyField(source='direction.name')

    class Meta:
        model = ActivitySubmission
        fields = [
            'id', 'task', 'date', 'task_details',
            'volunteer_id', 'volunteer_name',
            'status', 'created_at', 'description', 'points_awarded',
            'command', 'direction', 'command_title', 'direction_name'
        ]

# --- 🔥 ИСПРАВЛЕННЫЙ СПИСОК ДЛЯ КУРАТОРА ---
class VolunteerListSerializer(serializers.ModelSerializer):
    direction = VolunteerDirectionSerializer(many=True, read_only=True)
    
    # Используем DecimalField вместо IntegerField, чтобы видеть баллы типа 0.5
    local_points = serializers.DecimalField(max_digits=10, decimal_places=1, read_only=True)
    
    # === ГЛАВНОЕ ИСПРАВЛЕНИЕ ===
    # Добавляем рассчитанное нами честное "Всего"
    calculated_total = serializers.DecimalField(max_digits=10, decimal_places=1, read_only=True)
    
    yellow_card_count = serializers.IntegerField(read_only=True)
    volunteer_commands = serializers.SerializerMethodField()

    class Meta:
        model = Volunteer
        fields = [
            'id', 'name', 'login', 'direction', 
            'calculated_total', # Заменили 'point' на это поле
            'local_points', 
            'yellow_card_count', 
            'volunteer_commands'
        ]

    def get_volunteer_commands(self, obj):
        # Оптимально возвращаем список команд
        return obj.volunteer_commands.values('id', 'title')

# --- Анкета ---
class VolunteerApplicationSerializer(serializers.ModelSerializer):
    direction = serializers.PrimaryKeyRelatedField(queryset=VolunteerDirection.objects.all(), required=False)

    class Meta:
        model = VolunteerApplication
        fields = ['id', 'full_name', 'phone_number', 'direction', 'status']

# --- Вспомогательные ---
class VolunteerLoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(login=attrs['login'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError("Неверные данные")
        attrs['user'] = user
        return attrs

class BotAuthSerializer(serializers.Serializer):
    access_type = serializers.ChoiceField(choices=[('volunteer', 'volunteer'), ('curator', 'curator'), ('commands', 'commands')])
    password = serializers.CharField()

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ['id', 'volunteer', 'direction', 'date', 'status']

class BulkAttendanceSerializer(serializers.Serializer):
    direction_id = serializers.IntegerField()
    date = serializers.DateField()
    records = serializers.ListField(
        child=serializers.DictField()
    )