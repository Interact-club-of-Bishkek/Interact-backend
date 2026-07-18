from rest_framework import serializers
from .models import Command, Question, Application, Attachment, BoardApplication, BoardAttachment, BoardPosition, BoardQuestion

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'label', 'field_type']

class CommandSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Command
        # Добавляем 'direction', чтобы куратор мог найти свои команды по ID направления
        fields = ['id', 'title', 'slug', 'description', 'start_date', 'end_date', 'questions', 'leader', 'direction']
        
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
    
class BoardQuestionSerializer(serializers.ModelSerializer):

    class Meta:

        model = BoardQuestion

        fields = [
            "id",
            "label",
            "field_type",
            "required",
            "order",
            "options"
        ]




class BoardAttachmentSerializer(serializers.ModelSerializer):

    class Meta:

        model = BoardAttachment

        fields = [
            "id",
            "file",
            "label"
        ]




class BoardPositionSerializer(serializers.ModelSerializer):

    questions = BoardQuestionSerializer(
        many=True,
        read_only=True
    )


    class Meta:

        model = BoardPosition

        fields = [
            "id",
            "title",
            "slug",
            "description",
            "start_date",
            "end_date",
            "questions"
        ]





class BoardApplicationSerializer(serializers.ModelSerializer):

    files = BoardAttachmentSerializer(
        many=True,
        read_only=True
    )


    class Meta:

        model = BoardApplication

        fields = [
            "id",
            "board_position",
            "applicant",
            "answers",
            "status",
            "created_at",
            "files"
        ]
        

