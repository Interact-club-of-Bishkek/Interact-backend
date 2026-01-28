import json
import os
from django.utils import timezone

from django.shortcuts import render, get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import Command, Application, Attachment
from .serializers import CommandSerializer, ApplicationSerializer

# Список команд
class CommandListView(generics.ListAPIView):
    queryset = Command.objects.all()
    serializer_class = CommandSerializer
    permission_classes = [AllowAny]

# Деталка команды
class CommandDetailView(generics.RetrieveAPIView):
    queryset = Command.objects.all()
    serializer_class = CommandSerializer
    lookup_field = 'slug'
    permission_classes = [AllowAny]

# Список и создание заявок
from django.utils import timezone

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
            # Получаем команду
            command_slug = request.data.get('command_slug')
            command = get_object_or_404(Command, slug=command_slug)

            now = timezone.now()

            # Проверка начала и конца набора
            if command.start_date and now < command.start_date:
                return Response(
                    {"error": "Набор ещё не открыт. Ожидайте, мы скоро объявим!"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if command.end_date and now > command.end_date:
                return Response(
                    {"error": "Набор завершён."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Парсим текстовые ответы
            answers_raw = request.data.get('answers', '{}')
            answers = json.loads(answers_raw)

            # Создаем заявку
            app = Application.objects.create(
                command=command,
                answers=answers
            )

            # Сохраняем все файлы
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



# Обновление статуса
class ApplicationUpdateStatusView(generics.UpdateAPIView):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [AllowAny]

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.status = 'accepted'
        instance.save()
        return Response(self.get_serializer(instance).data)

# Страницы-заглушки для рендера
def volunteer_page(request):
    return render(request, 'commands/applications.html')

def curator_page(request):
    return render(request, 'commands/teamliders.html')