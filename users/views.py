import io
import os
from django.db import transaction
from django.conf import settings
from django.http import FileResponse
from django.views.generic import TemplateView
from django.db.models import Q
from django.db import models
from rest_framework import viewsets, generics, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from directions.models import VolunteerDirection
# ReportLab для генерации PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .models import (
    Volunteer, VolunteerApplication, BotAccessConfig, 
    ActivityTask, ActivitySubmission
)
from .serializers import (
    VolunteerSerializer, VolunteerLoginSerializer, VolunteerRegisterSerializer,
    VolunteerApplicationSerializer, ActivityTaskSerializer, 
    ActivitySubmissionSerializer, VolunteerDirectionSerializer, CommandSerializer
)

# ---------------- АВТОРИЗАЦИЯ И ПРОФИЛЬ ----------------

class VolunteerLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VolunteerLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        volunteer = serializer.validated_data.get("user") or serializer.validated_data.get("volunteer")
        
        # --- ОБНОВЛЕНИЕ РОЛИ ПЕРЕД ОТВЕТОМ ---
        from directions.models import VolunteerDirection
        from commands.models import Command
        
        is_responsible = VolunteerDirection.objects.filter(responsible=volunteer).exists()
        is_leader = Command.objects.filter(leader=volunteer).exists()
        
        if is_responsible or is_leader:
            if volunteer.role != 'curator':
                volunteer.role = 'curator'
                volunteer.is_staff = True
                volunteer.save()
        # -------------------------------------

        refresh = RefreshToken.for_user(volunteer)
        is_assigned = volunteer.direction.exists() or volunteer.commands.exists()
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'role': volunteer.role,  
            'name': volunteer.name or volunteer.login,
            'is_assigned': is_assigned
        })

class VolunteerRegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = VolunteerRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "role": user.role,
                "is_assigned": False,
                "user": VolunteerSerializer(user, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VolunteerProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = VolunteerSerializer

    def get_object(self):
        return self.request.user


# ---------------- ЛИЧНЫЙ КАБИНЕТ ВОЛОНТЕРА ----------------

class VolunteerActivityViewSet(viewsets.ModelViewSet):
    # Убедись, что queryset не пустой (это критично для роутера)
    queryset = ActivitySubmission.objects.all()
    serializer_class = ActivitySubmissionSerializer
    permission_classes = [IsAuthenticated]
    # Явно разрешаем методы
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return ActivitySubmission.objects.filter(volunteer=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(volunteer=self.request.user)

# users/views.py

class DiscoveryListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        # Явно импортируем модели
        from directions.models import VolunteerDirection
        from commands.models import Command

        # 1. Получаем ВСЕ направления для выпадающего списка
        all_directions = VolunteerDirection.objects.all()
        
        # 2. Получаем только ТЕ команды, в которых состоит юзер
        user_commands = user.commands.all()

        # 3. Фильтруем задания (те, что подходят юзеру)
        tasks = ActivityTask.objects.filter(
            Q(direction__in=user.direction.all()) | 
            Q(command__in=user.commands.all())
        ).distinct()

        return Response({
            "directions": VolunteerDirectionSerializer(all_directions, many=True).data,
            "commands": CommandSerializer(user_commands, many=True).data,
            "available_tasks": ActivityTaskSerializer(tasks, many=True).data
        })
# ---------------- ПАНЕЛЬ КУРАТОРА ----------------

class CuratorSubmissionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated] # Убедись, что тут нет IsAdminUser
    serializer_class = ActivitySubmissionSerializer

    def get_queryset(self):
        user = self.request.user
        # Если не админ и не куратор — пустой список
        if user.role not in ['curator', 'admin'] and not user.is_superuser:
            return ActivitySubmission.objects.none()
            
        if user.is_superuser or user.role == 'admin':
            return ActivitySubmission.objects.all().order_by('-created_at')
            
        # Для куратора — только его направления
        return ActivitySubmission.objects.filter(
            models.Q(task__direction__responsible=user) | 
            models.Q(task__command__leader=user)
        ).distinct().order_by('-created_at')

# ---------------- АНКЕТЫ И КАНБАН ----------------

class VolunteerApplicationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = VolunteerApplicationSerializer
    queryset = VolunteerApplication.objects.all()

    def perform_create(self, serializer):
        # Извлекаем команды из данных, так как их нельзя передать в create напрямую
        validated_data = serializer.validated_data
        commands_data = validated_data.pop('commands', [])
        
        with transaction.atomic():
            # 1. Создаем или обновляем анкету БЕЗ команд
            application, created = VolunteerApplication.objects.update_or_create(
                volunteer=self.request.user,
                defaults=validated_data
            )
            
            # 2. Теперь используем .set(), чтобы привязать команды
            if commands_data:
                application.commands.set(commands_data)
            
            # 3. Синхронизируем данные с профилем волонтера
            user = self.request.user
            user.name = application.full_name
            user.phone_number = application.phone_number
            
            # Привязываем одно направление к юзеру
            if application.direction:
                user.direction.set([application.direction])
            
            # Привязываем команды к юзеру
            if commands_data:
                user.commands.set(commands_data)
            
            # Проверяем роль куратора
            from directions.models import VolunteerDirection
            if VolunteerDirection.objects.filter(responsible=user).exists():
                user.role = 'curator'
                user.is_staff = True
            
            user.save()

# ---------------- PDF ГЕНЕРАЦИЯ (С кириллицей) ----------------

class DownloadPDFBase(APIView):
    permission_classes = [AllowAny]

    def get_pdf_response(self, volunteers, title, filename):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        
        font_path = os.path.join(settings.BASE_DIR, 'FreeSans.ttf')
        font_name = 'FreeSans' if os.path.exists(font_path) else 'Helvetica'
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('FreeSans', font_path))

        elements.append(Paragraph(title, ParagraphStyle('T', fontName=font_name, fontSize=18, alignment=1)))
        
        data = [['№', 'ФИО', 'Телефон']]
        for i, v in enumerate(volunteers):
            data.append([str(i+1), v.full_name, v.phone_number])
        
        t = Table(data, colWidths=[30, 300, 150])
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), font_name),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ]))
        elements.append(t)
        doc.build(elements)
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=filename)

class DownloadInterviewScheduleView(DownloadPDFBase):
    def get(self, request):
        vols = VolunteerApplication.objects.filter(status='interview').order_by('full_name')
        return self.get_pdf_response(vols, "Расписание собеседований", "Interviews.pdf")

class DownloadAcceptedNamesView(DownloadPDFBase):
    def get(self, request):
        vols = VolunteerApplication.objects.filter(status='accepted').order_by('full_name')
        return self.get_pdf_response(vols, "Принятые волонтеры", "Accepted.pdf")

# ---------------- HTML VIEWS ----------------

class VolunteerViewSet(viewsets.ModelViewSet):
    serializer_class = VolunteerSerializer
    permission_classes = [IsAuthenticated]
    queryset = Volunteer.objects.none()
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['curator', 'admin']:
            return Volunteer.objects.filter(
                Q(direction__in=user.direction.all()) | Q(commands__in=user.commands.all())
            ).distinct().order_by('-point')
        return Volunteer.objects.filter(id=user.id)

class VolunteerColumnsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Логика получения волонтеров, разбитых по колонкам (статусам анкеты)
        from .models import VolunteerApplication
        
        # Пример простой группировки
        columns = {
            "submitted": VolunteerApplicationSerializer(VolunteerApplication.objects.filter(status='submitted'), many=True).data,
            "interview": VolunteerApplicationSerializer(VolunteerApplication.objects.filter(status='interview'), many=True).data,
            "accepted": VolunteerApplicationSerializer(VolunteerApplication.objects.filter(status='accepted'), many=True).data,
        }
        return Response(columns)

class CuratorPanelView(TemplateView): template_name = "volunteers/curator_panel.html"
class VolunteerCabinetView(TemplateView): template_name = "volunteers/volunteer_cabinet.html"
class LoginPageView(TemplateView): template_name = "volunteers/login.html"
class VolunteerBoardView(TemplateView): template_name = "volunteers/columns.html"