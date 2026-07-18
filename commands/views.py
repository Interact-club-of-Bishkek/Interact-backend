import json
import os
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

# 🔥 ИМПОРТИРУЕМ ВСЕ МОДЕЛИ (И КОМАНДЫ, И БОРД)
from .models import (
    Command, Application, Attachment,
    BoardPosition, BoardApplication, BoardAttachment
)

# 🔥 ИМПОРТИРУЕМ ВСЕ СЕРИАЛИЗАТОРЫ
from .serializers import (
    CommandSerializer, ApplicationSerializer,
    BoardPositionSerializer, BoardApplicationSerializer
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
    permission_classes = [AllowAny]

    def get_queryset(self):
        user = self.request.user

        queryset = Application.objects.all().order_by("-created_at")

        if not (
            user.is_superuser or
            getattr(user, "role", "") in ["admin", "president"]
        ):
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
            answers = json.loads(answers_raw)

            app = Application.objects.create(command=command, answers=answers)

            for key in request.FILES:
                for f in request.FILES.getlist(key):
                    Attachment.objects.create(
                        application=app,
                        file=f,
                        label=key.replace('TEXT__','')
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
# API ДЛЯ НАБОРА В БОРД
# ==========================================
class BoardPositionListCreateView(generics.ListCreateAPIView):
    queryset = BoardPosition.objects.all()
    serializer_class = BoardPositionSerializer
    permission_classes = [AllowAny] # Измени на IsAuthenticated если создавать могут только админы

class BoardPositionDetailView(generics.RetrieveAPIView):
    queryset = BoardPosition.objects.all()
    serializer_class = BoardPositionSerializer
    lookup_field = 'slug'
    permission_classes = [AllowAny]

class BoardApplicationListCreateView(generics.ListCreateAPIView):
    serializer_class = BoardApplicationSerializer
    # 🔥 ВАЖНО: Только авторизованные могут подавать заявки в Борд,
    # чтобы мы могли привязать их ФИО и профиль.
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        user = self.request.user

        queryset = BoardApplication.objects.all().order_by("-created_at")

        # Президент и админ видят все заявки
        if user.is_superuser or getattr(user, "role", "") in ["admin", "president"]:
            pass
        else:
            # Остальные только на свои позиции
            queryset = queryset.filter(board_position__leader=user)

        slug = self.request.query_params.get("slug")
        if slug:
            queryset = queryset.filter(board_position__slug=slug)

        return queryset

    def post(self, request, *args, **kwargs):
        try:
            board_slug = request.data.get('board_slug')
            board_position = get_object_or_404(BoardPosition, slug=board_slug)
            now = timezone.now()

            if board_position.start_date and now < board_position.start_date:
                return Response({"error": "Набор ещё не открыт."}, status=status.HTTP_400_BAD_REQUEST)
            if board_position.end_date and now > board_position.end_date:
                return Response({"error": "Набор завершён."}, status=status.HTTP_400_BAD_REQUEST)

            answers_raw = request.data.get('answers', '{}')
            answers = json.loads(answers_raw)

            # 🔥 СОЗДАЕМ ЗАЯВКУ В БОРД И СРАЗУ ПРИВЯЗЫВАЕМ ПОЛЬЗОВАТЕЛЯ (applicant)
            app = BoardApplication.objects.create(
                board_position=board_position,
                applicant=request.user, # Берем ФИО и телефон из этого пользователя
                answers=answers
            )

            for key in request.FILES:
                for f in request.FILES.getlist(key):
                    BoardAttachment.objects.create(
                        application=app,
                        file=f,
                        label=key.replace('TEXT__','')
                    )

            return Response({"status": "success", "id": app.id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class BoardApplicationUpdateStatusView(generics.UpdateAPIView):
    queryset = BoardApplication.objects.all()
    serializer_class = BoardApplicationSerializer
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        if not has_board_management_rights(request.user, instance.board_position):
            return Response({"error": "Нет прав для принятия заявки"}, status=status.HTTP_403_FORBIDDEN)

        instance.status = 'accepted'
        instance.save()
        return Response(self.get_serializer(instance).data)

class AddVolunteerToBoardView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        board_position = get_object_or_404(BoardPosition, pk=pk)
        if not has_board_management_rights(request.user, board_position):
            return Response({"error": "Нет прав"}, status=status.HTTP_403_FORBIDDEN)
        
        vol_ids = request.data.get('volunteer_ids', [])
        if not vol_ids:
            single_id = request.data.get('volunteer_id')
            if single_id: vol_ids = [single_id]
        if not vol_ids:
            return Response({"error": "Не выбраны кандидаты"}, status=status.HTTP_400_BAD_REQUEST)

        volunteers = Volunteer.objects.filter(id__in=vol_ids)
        board_position.members.add(*volunteers)
        return Response({"status": "success", "message": "Добавлено в борд"})

class RemoveVolunteerFromBoardView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        board_position = get_object_or_404(BoardPosition, pk=pk)
        if not has_board_management_rights(request.user, board_position):
            return Response({"error": "Нет прав"}, status=status.HTTP_403_FORBIDDEN)

        volunteer_id = request.data.get('volunteer_id')
        if not volunteer_id:
            return Response({"error": "Не передан volunteer_id"}, status=status.HTTP_400_BAD_REQUEST)

        volunteer = get_object_or_404(Volunteer, id=volunteer_id)
        board_position.members.remove(volunteer)
        return Response({"status": "success", "message": "Участник исключен из борда"})


# ==========================================
# ЗАГЛУШКИ HTML СТРАНИЦ
# ==========================================
def volunteer_page(request):
    return render(request, 'commands/applications.html')

def curator_page(request):
    return render(request, 'commands/teamliders.html')

def board_page(request):
    return render(request, 'commands/board.html')



def president_page(request):
    # Просто отдаем HTML. Вся авторизация - через токены внутри JS (фронтенд)
    return render(request, 'volunteers/president_dashboard.html')