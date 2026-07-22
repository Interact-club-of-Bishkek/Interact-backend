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
    board_title = serializers.CharField(source='board_position.title', read_only=True)
    files = BoardAttachmentSerializer(source='attachments', many=True, read_only=True)
    
    applicant_name = serializers.SerializerMethodField()
    applicant_phone = serializers.SerializerMethodField()
    
    # 🔥 НОВОЕ: Поле для красивых ответов в Борде
    formatted_answers = serializers.SerializerMethodField()

    class Meta:
        model = BoardApplication
        fields = '__all__'

    def get_applicant_name(self, obj):
        if obj.answers and isinstance(obj.answers, dict):
            values = list(obj.answers.values())
            return str(values[0]) if values else 'Без имени'
        return 'Без имени'

    def get_applicant_phone(self, obj):
        if obj.answers and isinstance(obj.answers, dict):
            for key, value in obj.answers.items():
                if 'phone' in key.lower() or 'телефон' in key.lower() or 'номер' in key.lower():
                    return str(value)
        return 'Нет данных'
        
    # 🔥 НОВЫЙ МЕТОД: Расшифровка q_XXX для Борда
    def get_formatted_answers(self, obj):
        if not obj.answers or not isinstance(obj.answers, dict):
            return {}
        
        q_ids = []
        for key in obj.answers.keys():
            if key.startswith('q_') and key[2:].isdigit():
                q_ids.append(int(key[2:]))
        
        # Для борда берем вопросы из BoardQuestion
        questions = BoardQuestion.objects.filter(id__in=q_ids)
        q_map = {f"q_{q.id}": q.label for q in questions}
        
        readable_answers = {}
        for key, value in obj.answers.items():
            question_text = q_map.get(key, key)
            readable_answers[question_text] = value
            
        return readable_answers
        

