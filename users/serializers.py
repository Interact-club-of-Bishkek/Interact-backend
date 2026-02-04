from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import Volunteer, VolunteerApplication, ActivityTask, ActivitySubmission
from directions.models import VolunteerDirection
from commands.models import Command

# --- Регистрация ---
class VolunteerRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Volunteer
        fields = ['login', 'password']

    def create(self, validated_data):
        # Используем встроенный метод для корректного хеширования пароля
        return Volunteer.objects.create_user(**validated_data)

# --- Справочники ---
class VolunteerDirectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VolunteerDirection
        fields = ['id', 'name']

class CommandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Command
        fields = ['id', 'title', 'slug']

# --- Система Активностей ---
class ActivityTaskSerializer(serializers.ModelSerializer):
    direction_name = serializers.ReadOnlyField(source='direction.name')
    command_name = serializers.ReadOnlyField(source='command.title')

    class Meta:
        model = ActivityTask
        fields = ['id', 'title', 'description', 'points', 'direction', 'direction_name', 'command', 'command_name']

class ActivitySubmissionSerializer(serializers.ModelSerializer):
    task_details = ActivityTaskSerializer(source='task', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    volunteer_name = serializers.ReadOnlyField(source='volunteer.name')

    class Meta:
        model = ActivitySubmission
        fields = ['id', 'task', 'task_details', 'volunteer_name', 'status', 'status_display', 'created_at']
        read_only_fields = ['status', 'created_at']

# --- Профиль Волонтера ---
class VolunteerSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)
    direction = VolunteerDirectionSerializer(many=True, read_only=True)
    commands = CommandSerializer(many=True, read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = Volunteer
        fields = [
            'id', 'login', 'name', 'phone_number', 'email', 'image_url', # email оставляем в полях, но он может быть пуст
            'role', 'role_display', 'direction', 'commands', 
            'point', 'yellow_card'
        ]
        read_only_fields = ['point', 'yellow_card', 'role', 'login']

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None

# --- Анкета (Шаг 2) ---
class VolunteerApplicationSerializer(serializers.ModelSerializer):
    # Указываем явно для обработки ID
    direction = serializers.PrimaryKeyRelatedField(queryset=VolunteerDirection.objects.all(), required=False)
    commands = serializers.PrimaryKeyRelatedField(many=True, queryset=Command.objects.all(), required=False)

    class Meta:
        model = VolunteerApplication
        fields = ['id', 'full_name', 'phone_number', 'direction', 'commands', 'status']
# --- Остальное ---
class VolunteerLoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(login=attrs['login'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError("Неверные данные")
        attrs['user'] = user
        return attrs

class VolunteerApplicationStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VolunteerApplication
        fields = ['status']

class BotAuthSerializer(serializers.Serializer):
    access_type = serializers.ChoiceField(choices=[('volunteer', 'volunteer'), ('curator', 'curator'), ('commands', 'commands')])
    password = serializers.CharField()