from rest_framework import serializers
from .models import Command, Question, Application, Attachment

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['label', 'field_type']

class CommandSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Command
        # ОБЯЗАТЕЛЬНО добавляем эти поля сюда:
        fields = ['id', 'title', 'slug', 'description', 'start_date', 'end_date', 'questions']

class AttachmentSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ['id', 'file', 'label']

    def get_file(self, obj):
        if not obj.file:
            return None
        request = self.context.get('request')
        # Строим полный URL (http://127.0.0.1:8000/media/...)
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url

class ApplicationSerializer(serializers.ModelSerializer):
    files = AttachmentSerializer(many=True, read_only=True)
    command_title = serializers.ReadOnlyField(source='command.title')
    command_slug = serializers.ReadOnlyField(source='command.slug')

    class Meta:
        model = Application
        fields = ['id', 'command', 'command_slug', 'command_title', 'answers', 'status', 'created_at', 'files']