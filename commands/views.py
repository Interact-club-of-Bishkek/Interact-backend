from rest_framework import generics, status
from rest_framework.response import Response
from .models import Command, Application, Attachment
from django.shortcuts import render
import json
from .serializers import CommandSerializer, ApplicationSerializer
from rest_framework.permissions import AllowAny

# Список всех команд для выпадающего списка
class CommandListView(generics.ListAPIView):
    queryset = Command.objects.all()
    serializer_class = CommandSerializer
    permission_classes = [AllowAny]

# Деталка команды по slug (вопросы)
class CommandDetailView(generics.RetrieveAPIView):
    queryset = Command.objects.all()
    serializer_class = CommandSerializer
    lookup_field = 'slug'
    permission_classes = [AllowAny]

# Создание заявки и список для куратора
class ApplicationListCreateView(generics.ListCreateAPIView):
    queryset = Application.objects.all().order_by('-created_at')
    serializer_class = ApplicationSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # Правильный способ: вызываем .all() от базового кверисета 
        # или обращаемся к модели напрямую
        queryset = Application.objects.all().order_by('-created_at')
        
        slug = self.request.query_params.get('slug')
        if slug:
            return queryset.filter(command__slug=slug)
        return queryset
    
    def post(self, request, *args, **kwargs):
        # 1. Создаем заявку
        app = Application.objects.create(
            command=Command.objects.get(slug=request.data['command_slug']),
            answers=json.loads(request.data['answers'])
        )
        # 2. Сохраняем файлы
        files = request.FILES.getlist('uploaded_files')
        for f in files:
            Attachment.objects.create(application=app, file=f, label=f.name)
        return Response(status=201)
# Изменение статуса (Принять заявку)
class ApplicationUpdateStatusView(generics.UpdateAPIView):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [AllowAny]

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.status = 'accepted'
        instance.save()
        return Response(self.get_serializer(instance).data)
    


def volunteer_page(request):
    return render(request, 'commands/applications.html')

def curator_page(request):
    return render(request, 'commands/teamliders.html')