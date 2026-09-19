import json
import os
import re
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

# 🔥 ИМПОРТИРУЕМ ВСЕ МОДЕЛИ
from .models import (
    Command, Question, Application, Attachment,
)

# 🔥 ИМПОРТИРУЕМ ВСЕ СЕРИАЛИЗАТОРЫ
from .serializers import (
    CommandSerializer, ApplicationSerializer,
)

try:
    from users.models import Volunteer
except ImportError:
    from django.contrib.auth import get_user_model
    Volunteer = get_user_model()


# ==========================================
# ПРОВЕРКИ ПРАВ ДОСТУПА
# ==========================================
def has_command_management_rights(user, command):
    if user.is_superuser:
        return True
    user_role = getattr(user, 'role', '')
    if user_role in ['admin', 'president']:
        return True
    if command.leader == user:
        return True
    return False

def has_board_management_rights(user, board_position):
    if user.is_superuser:
        return True
    user_role = getattr(user, 'role', '')
    if user_role in ['admin', 'president']:
        return True
    if getattr(board_position, 'leader', None) == user:
        return True
    return False


# ==========================================
# API ДЛЯ ОБЫЧНЫХ КОМАНД
# ==========================================
class CommandListView(generics.ListAPIView):
    queryset = Command.objects.all()
    serializer_class = CommandSerializer
    permission_classes = [AllowAny]

class CommandDetailView(generics.RetrieveAPIView):
    queryset = Command.objects.all()
    serializer_class = CommandSerializer
    lookup_field = 'slug'
    permission_classes = [AllowAny]

class ApplicationListCreateView(generics.ListCreateAPIView):
    serializer_class = ApplicationSerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return Application.objects.none()

        queryset = Application.objects.all().order_by("-created_at")

        is_management = user.is_superuser or getattr(user, "role", "") in ["admin", "president"]
        
        if not is_management:
            queryset = queryset.filter(command__leader=user)

        slug = self.request.query_params.get("slug")
        if slug:
            queryset = queryset.filter(command__slug=slug)

        return queryset

    def post(self, request, *args, **kwargs):
        try:
            command_slug = request.data.get('command_slug')
            command = get_object_or_404(Command, slug=command_slug)
            now = timezone.now()

            if command.start_date and now < command.start_date:
                return Response({"error": "Набор ещё не открыт."}, status=status.HTTP_400_BAD_REQUEST)
            if command.end_date and now > command.end_date:
                return Response({"error": "Набор завершён."}, status=status.HTTP_400_BAD_REQUEST)

            answers_raw = request.data.get('answers', '{}')
            if isinstance(answers_raw, str):
                answers = json.loads(answers_raw)
            else:
                answers = answers_raw

            # 1. Определение волонтера (если юзер авторизован)
            volunteer = None
            if request.user.is_authenticated:
                volunteer = getattr(request.user, 'volunteer', None) or request.user

            # 2. Создание заявки
            app = Application.objects.create(
                command=command, 
                volunteer=volunteer,
                answers=answers
            )

            # 3. Обработка файлов и привязка к Question
            for key in request.FILES:
                files = request.FILES.getlist(key)
                
                # Попытка парсинга ID вопроса из названия ключа (например: "question_12" или "question_12[]")
                question_obj = None
                clean_key = key.replace('TEXT__', '').replace('[]', '')
                
                # Поиск ID вопроса через регулярные выражения или по строгому совпадению
                match = re.search(r'question_(\d+)', clean_key)
                if match:
                    question_id = match.group(1)
                    question_obj = Question.objects.filter(id=question_id, command=command).first()
                elif clean_key.isdigit():
                    question_obj = Question.objects.filter(id=clean_key, command=command).first()

                label_text = question_obj.label if question_obj else clean_key

                for f in files:
                    Attachment.objects.create(
                        application=app,
                        question=question_obj,  # Указываем ссылку на вопрос
                        file=f,
                        label=label_text
                    )

            return Response({"status": "success", "id": app.id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ApplicationUpdateStatusView(generics.UpdateAPIView):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        if not has_command_management_rights(request.user, instance.command):
            return Response({"error": "Нет прав для принятия заявки"}, status=status.HTTP_403_FORBIDDEN)

        instance.status = 'accepted'
        instance.save()
        return Response(self.get_serializer(instance).data)


class AddVolunteerToCommandView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        command = get_object_or_404(Command, pk=pk)
        if not has_command_management_rights(request.user, command):
            return Response({"error": "Нет прав"}, status=status.HTTP_403_FORBIDDEN)
        
        vol_ids = request.data.get('volunteer_ids', [])
        if not vol_ids:
            single_id = request.data.get('volunteer_id')
            if single_id: vol_ids = [single_id]
        if not vol_ids:
            return Response({"error": "Не выбраны волонтеры"}, status=status.HTTP_400_BAD_REQUEST)

        volunteers = Volunteer.objects.filter(id__in=vol_ids)
        command.volunteers.add(*volunteers)
        return Response({"status": "success", "message": f"Добавлено участников: {len(volunteers)}"})


class RemoveVolunteerFromCommandView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        command = get_object_or_404(Command, pk=pk)
        if not has_command_management_rights(request.user, command):
            return Response({"error": "Нет прав"}, status=status.HTTP_403_FORBIDDEN)

        volunteer_id = request.data.get('volunteer_id')
        if not volunteer_id:
            return Response({"error": "Не передан volunteer_id"}, status=status.HTTP_400_BAD_REQUEST)

        volunteer = get_object_or_404(Volunteer, id=volunteer_id)
        command.volunteers.remove(volunteer)
        return Response({"status": "success", "message": "Участник успешно исключен из команды"})


# ==========================================
# ЗАГЛУШКИ HTML СТРАНИЦ
# ==========================================
def volunteer_page(request):
    return render(request, 'commands/applications.html')


def president_page(request):
    return render(request, 'volunteers/president_dashboard.html')
