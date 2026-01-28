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
        fields = ['id', 'title', 'slug', 'questions']

class ApplicationSerializer(serializers.ModelSerializer):
    command_slug = serializers.SlugRelatedField(
        slug_field='slug', 
        queryset=Command.objects.all(), 
        source='command'
    )

    class Meta:
        model = Application
        fields = ['id', 'command_slug', 'answers', 'status', 'created_at']

class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ['file', 'label']

class ApplicationSerializer(serializers.ModelSerializer):
    files = AttachmentSerializer(many=True, read_only=True)
    command_title = serializers.ReadOnlyField(source='command.title')

    class Meta:
        model = Application
        fields = ['id', 'command', 'answers', 'status', 'created_at', 'files', 'command_title']