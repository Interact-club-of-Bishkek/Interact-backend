import json
import os
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView
from django.contrib.auth.mixins import UserPassesTestMixin
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import Command, Application, Attachment
from .serializers import CommandSerializer, ApplicationSerializer

try:
    from users.models import Volunteer
except ImportError:
    from django.contrib.auth import get_user_model
    Volunteer = get_user_model()


# --- Вспомогательная функция для проверки прав ---
def has_command_management_rights(user, command):
    """
    Проверяет, имеет ли пользователь право управлять составом команды.
    """
    if user.is_superuser:
        return True
    
    # Доступ для ролей админа и президента (глобальный доступ)
    user_role = getattr(user, 'role', '')
    if user_role in ['admin', 'president']:
        return True
        
    # Доступ для лидера конкретной команды
    if command.leader == user:
        return True
        
    # (Опционально) Доступ для куратора направления
    # if user_role == 'curator' and command.direction in user.direction.all():
    #     return True

    return False


# --- Кабинет Президента ---
# --- Кабинет Президента ---
class PresidentDashboardView(UserPassesTestMixin, TemplateView):
    template_name = 'president_dashboard.html'

    def test_func(self):
        return self.request.user.is_authenticated and getattr(self.request.user, 'role', '') == 'president'

    def handle_no_permission(self):
        return redirect('/login/')

# --- Список команд ---
class CommandListView(generics.ListAPIView):
    queryset = Command.objects.all()
    serializer_class = CommandSerializer
    permission_classes = [AllowAny]

# --- Деталка команды ---
class CommandDetailView(generics.RetrieveAPIView):
    queryset = Command.objects.all()
    serializer_class = CommandSerializer
    lookup_field = 'slug'
    permission_classes = [AllowAny]

# --- Список и создание заявок ---
class ApplicationListCreateView(generics.ListCreateAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # Президенты видят все заявки, остальные только свои (настраивается здесь или во фронте)
        queryset = Application.objects.all().order_by('-created_at')
        slug = self.request.query_params.get('slug')
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


# --- Обновление статуса заявки ---
class ApplicationUpdateStatusView(generics.UpdateAPIView):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated] # Желательно закрыть от неавторизованных

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Проверка прав (кто угодно не должен принимать заявки)
        if not has_command_management_rights(request.user, instance.command):
            return Response({"error": "Нет прав для принятия заявки"}, status=status.HTTP_403_FORBIDDEN)

        instance.status = 'accepted'
        instance.save()
        return Response(self.get_serializer(instance).data)


# ==========================================
# Управление составом: Добавление
# ==========================================
class AddVolunteerToCommandView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        command = get_object_or_404(Command, pk=pk)
        
        if not has_command_management_rights(request.user, command):
            return Response({"error": "Нет прав на управление этой командой"}, status=status.HTTP_403_FORBIDDEN)

        vol_ids = request.data.get('volunteer_ids', [])
        
        if not vol_ids:
            single_id = request.data.get('volunteer_id')
            if single_id:
                vol_ids = [single_id]

        if not vol_ids:
            return Response({"error": "Не выбраны волонтеры"}, status=status.HTTP_400_BAD_REQUEST)

        volunteers = Volunteer.objects.filter(id__in=vol_ids)
        command.volunteers.add(*volunteers)
        
        return Response({
            "status": "success", 
            "message": f"Добавлено участников: {len(volunteers)}"
        })


# ==========================================
# Управление составом: Удаление (НОВОЕ)
# ==========================================
class RemoveVolunteerFromCommandView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        command = get_object_or_404(Command, pk=pk)
        
        if not has_command_management_rights(request.user, command):
            return Response({"error": "Нет прав на управление этой командой"}, status=status.HTTP_403_FORBIDDEN)

        volunteer_id = request.data.get('volunteer_id')
        if not volunteer_id:
            return Response({"error": "Не передан volunteer_id"}, status=status.HTTP_400_BAD_REQUEST)

        volunteer = get_object_or_404(Volunteer, id=volunteer_id)
        
        # Удаляем волонтера из команды
        command.volunteers.remove(volunteer)
        
        return Response({
            "status": "success", 
            "message": "Участник успешно исключен из команды"
        })


# --- Заглушки ---
# --- Заглушки ---
def volunteer_page(request):
    return render(request, 'commands/applications.html')

def curator_page(request):
    return render(request, 'commands/teamliders.html')

def president_page(request):
    # Просто отдаем HTML. Проверка прав (токен) будет работать внутри JS-скрипта (init)
    return render(request, 'volunteers/president_dashboard.html')