from rest_framework import serializers
from .models import Command, Question, Application, Attachment
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
    command_title = serializers.CharField(source='command.title', read_only=True)
    # Используем 'files', так как в твоей модели Attachment прописано related_name='files'
    files = AttachmentSerializer(many=True, read_only=True) 
    
    # Поле для красивых ответов
    formatted_answers = serializers.SerializerMethodField()

    class Meta:
        model = Application
        # ЯВНО указываем все поля! Теперь DRF точно отдаст formatted_answers
        fields = [
            'id', 
            'command', 
            'command_title', 
            'volunteer', 
            'answers', 
            'formatted_answers', 
            'status', 
            'created_at',
            'files'
        ]
        
    def get_formatted_answers(self, obj):
        if not obj.answers or not isinstance(obj.answers, dict):
            return {}
        
        q_ids = []
        for key in obj.answers.keys():
            # Ищем ключи формата q_123
            if key.startswith('q_') and key[2:].isdigit():
                q_ids.append(int(key[2:]))
        
        # Вытаскиваем тексты вопросов из твоей модели Question (поле label)
        questions = Question.objects.filter(id__in=q_ids)
        q_map = {f"q_{q.id}": q.label for q in questions}
        
        readable_answers = {}
        for key, value in obj.answers.items():
            # Заменяем ключ на текст вопроса (если вопрос есть в базе)
            question_text = q_map.get(key, key)
            readable_answers[question_text] = value
            
        return readable_answers


