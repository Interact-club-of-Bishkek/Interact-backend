import json
import os
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
class ApplicationListCreateView(generics.ListCreateAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # Используем .all(), чтобы избежать RuntimeError и кеширования
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
            
            # Парсим ответы
            answers_raw = request.data.get('answers', '{}')
            answers = json.loads(answers_raw)

            # 1. Создаем заявку
            app = Application.objects.create(
                command=command,
                answers=answers
            )

            # 2. Сохраняем файлы с сохранением их оригинальных имен и расширений
            files = request.FILES.getlist('uploaded_files')
            for f in files:
                # Django автоматически обработает f.name, сохраняя расширение
                Attachment.objects.create(
                    application=app, 
                    file=f, 
                    label=f.name
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