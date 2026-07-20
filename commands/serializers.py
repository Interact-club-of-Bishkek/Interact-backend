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
    # 🔥 Добавляем название команды (проверь, что в модели Command поле называется именно title или name)
    command_title = serializers.CharField(source='command.title', read_only=True) # или command.name
    files = AttachmentSerializer(source='attachments', many=True, read_only=True) # Имя related_name из модели

    class Meta:
        model = Application
        fields = '__all__'
        
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
    # 🔥 Добавляем название позиции
    board_title = serializers.CharField(source='board_position.title', read_only=True) # или board_position.name
    files = BoardAttachmentSerializer(source='attachments', many=True, read_only=True)
    
    # 🔥 Достаем имя и телефон. Так как заявки подаются в JSON-формате, ищем значения в answers
    applicant_name = serializers.SerializerMethodField()
    applicant_phone = serializers.SerializerMethodField()

    class Meta:
        model = BoardApplication
        fields = '__all__'

    def get_applicant_name(self, obj):
        if obj.answers and isinstance(obj.answers, dict):
            # Берем первый ответ из JSON как имя (или укажи конкретный ключ, например obj.answers.get('q_name'))
            values = list(obj.answers.values())
            return str(values[0]) if values else 'Без имени'
        return 'Без имени'

    def get_applicant_phone(self, obj):
        if obj.answers and isinstance(obj.answers, dict):
            # Ищем ключ, в котором есть слово phone или телефон
            for key, value in obj.answers.items():
                if 'phone' in key.lower() or 'телефон' in key.lower() or 'номер' in key.lower():
                    return str(value)
        return 'Нет данных'
        

