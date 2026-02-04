import io
import os
from django.db import transaction
from django.conf import settings
# УДАЛИЛИ: from django.forms import DecimalField  <-- ЭТО БЫЛА ОШИБКА
from django.http import FileResponse
from django.views.generic import TemplateView

# ИЗМЕНЕНИЕ: Добавили DecimalField сюда
from django.db.models import Sum, Value, Q, DecimalField 
from django.db.models.functions import Coalesce
from django.db import models

from rest_framework import viewsets, generics, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from directions.models import VolunteerDirection
from rest_framework_simplejwt.tokens import RefreshToken
from commands.models import Command
from rest_framework import permissions

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
    ActivitySubmissionSerializer, VolunteerDirectionSerializer, CommandSerializer,
    VolunteerListSerializer
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
            # ИСПРАВЛЕНИЕ: меняем на куратора только если текущая роль — волонтер
            if volunteer.role == 'volunteer':
                volunteer.role = 'curator'
                volunteer.is_staff = True
                volunteer.save()
            # Если роль уже выше (напр. тимлид), просто проверяем доступ в админку
            elif not volunteer.is_staff:
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
            'is_assigned': is_assigned,
            'is_team_leader': is_leader,
            'is_direction_curator': is_responsible
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


class DiscoveryListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user

        # 1. Справочники
        all_directions = VolunteerDirection.objects.all()
        user_commands = user.commands.all()
        user_directions = user.direction.all()

        # 2. Логика задач (Общие + Командные)
        tasks = ActivityTask.objects.filter(
            Q(command__isnull=True) |   # Общие задачи
            Q(command__in=user_commands) # Задачи моих команд
        ).distinct()

        return Response({
            "all_directions": VolunteerDirectionSerializer(all_directions, many=True).data,
            "my_direction": VolunteerDirectionSerializer(user_directions, many=True).data,
            "my_commands": CommandSerializer(user_commands, many=True).data,
            "available_tasks": ActivityTaskSerializer(tasks, many=True).data
        })

# ---------------- ПАНЕЛЬ КУРАТОРА ----------------

class CuratorSubmissionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ActivitySubmissionSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role == 'admin':
            return ActivitySubmission.objects.all().order_by('-created_at')
            
        # Логика Куратора:
        # (А) Это задача его СПЕЦ. КОМАНДЫ (где он лидер)
        # ИЛИ
        # (Б) Заявку подал волонтер из ЕГО НАПРАВЛЕНИЯ (даже если задача общая)
        
        return ActivitySubmission.objects.filter(
            Q(task__command__leader=user) | 
            Q(volunteer__direction__responsible=user)
        ).distinct().order_by('-created_at')

# ---------------- АНКЕТЫ И КАНБАН ----------------

class VolunteerApplicationViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VolunteerApplicationSerializer
    queryset = VolunteerApplication.objects.all()

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser or user.role == 'admin':
            return VolunteerApplication.objects.all()

        return VolunteerApplication.objects.filter(
            commands__leader=user
        ).distinct()

    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        
        # 1. Извлекаем команды. 
        commands_data = validated_data.pop('commands', None)
        
        print(f"DEBUG: User={self.request.user}, Commands Data={commands_data}")

        with transaction.atomic():
            # 2. Создаем/Обновляем анкету (БЕЗ поля commands)
            application, created = VolunteerApplication.objects.update_or_create(
                volunteer=self.request.user,
                defaults=validated_data
            )
            
            # 3. Привязываем команды к АНКЕТЕ
            if commands_data is not None:
                application.commands.set(commands_data)
            
            # 4. СИНХРОНИЗАЦИЯ С ПРОФИЛЕМ ВОЛОНТЕРА
            user = self.request.user
            
            if application.full_name:
                user.name = application.full_name
            if application.phone_number:
                user.phone_number = application.phone_number
            
            if application.direction:
                user.direction.set([application.direction])
            
            if commands_data is not None:
                user.commands.set(commands_data)
            
            # Проверяем роль куратора
            from directions.models import VolunteerDirection
            from commands.models import Command 
            
            is_responsible = VolunteerDirection.objects.filter(responsible=user).exists()
            is_leader = Command.objects.filter(leader=user).exists() if hasattr(Command, 'leader') else False

            if is_responsible or is_leader:
                user.role = 'curator'
                user.is_staff = True
            
            user.save()

class VolunteerListView(generics.ListAPIView):
    serializer_class = VolunteerListSerializer  
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # 1. Если Админ — показываем всех
        if user.is_superuser or user.role == 'admin':
            return Volunteer.objects.all().annotate(
                local_points=Coalesce(
                    'point', 
                    Value(0),
                    output_field=DecimalField() # Теперь работает (берется из models)
                )
            )

        # 2. Логика Куратора
        my_directions = user.responsible_for_directions.all()
        my_commands = Command.objects.filter(leader=user)

        # 3. Фильтр списка людей
        queryset = Volunteer.objects.filter(
            Q(direction__in=my_directions) | 
            Q(commands__in=my_commands)
        ).distinct()

        # 4. СЧИТАЕМ БАЛЛЫ (local_points)
        queryset = queryset.annotate(
            local_points=Coalesce(
                Sum(
                    'submissions__task__points', 
                    filter=Q(submissions__status='approved') & (
                        Q(submissions__task__command__in=my_commands) |
                        Q(submissions__task__command__isnull=True)
                    )
                ),
                Value(0),
                output_field=DecimalField() # Теперь работает (берется из models)
            )
        )

        return queryset.exclude(id=user.id)

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