import json
import os
from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView # <--- Добавил
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated # <--- Добавил IsAuthenticated
from .models import Command, Application, Attachment
from .serializers import CommandSerializer, ApplicationSerializer

# Импортируем модель Волонтера (из приложения users)
# Если ваше приложение называется по-другому, поменяйте 'users'
try:
    from users.models import Volunteer
except ImportError:
    # Запасной вариант, если вдруг модель в другом месте (но обычно users)
    from django.contrib.auth import get_user_model
    Volunteer = get_user_model()

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
    permission_classes = [AllowAny]

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.status = 'accepted'
        instance.save()
        return Response(self.get_serializer(instance).data)

# ==========================================
# НОВЫЙ КЛАСС: Добавление волонтера в команду
# ==========================================
class AddVolunteerToCommandView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        command = get_object_or_404(Command, pk=pk)
        
        # Проверка прав
        if command.leader != request.user and not request.user.is_superuser:
            return Response({"error": "Нет прав"}, status=status.HTTP_403_FORBIDDEN)

        # Проверяем, пришел список ID или один ID
        vol_ids = request.data.get('volunteer_ids', [])
        
        # Если пришел один ID (старый формат), превращаем в список
        if not vol_ids:
            single_id = request.data.get('volunteer_id')
            if single_id:
                vol_ids = [single_id]

        if not vol_ids:
            return Response({"error": "Не выбраны волонтеры"}, status=status.HTTP_400_BAD_REQUEST)

        # Получаем волонтеров и массово добавляем
        volunteers = Volunteer.objects.filter(id__in=vol_ids)
        command.volunteers.add(*volunteers) # Звездочка распаковывает список
        
        return Response({
            "status": "success", 
            "message": f"Добавлено участников: {len(volunteers)}"
        })

# --- Заглушки ---
def volunteer_page(request):
    return render(request, 'commands/applications.html')

def curator_page(request):
    return render(request, 'commands/teamliders.html')