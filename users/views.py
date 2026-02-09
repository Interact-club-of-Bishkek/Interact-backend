import io
import os
from django.db import transaction
from django.conf import settings
from django.http import FileResponse
from django.views.generic import TemplateView
from django.db import models
# ВАЖНО: Импортируем DecimalField именно отсюда для ORM
from django.db.models import Sum, Value, Q, DecimalField, Count
from django.db.models.functions import Coalesce

from rest_framework import viewsets, generics, status, permissions
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken

# ReportLab для генерации PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Импорты моделей (лучше держать их вверху, если нет циклической зависимости)
from .models import (
    Attendance, Volunteer, VolunteerApplication, BotAccessConfig, 
    ActivityTask, ActivitySubmission, YellowCard
)
from directions.models import VolunteerDirection
from commands.models import Command

from .serializers import (
    BulkAttendanceSerializer, VolunteerSerializer, VolunteerLoginSerializer, VolunteerRegisterSerializer,
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
        # Проверяем, является ли пользователь ответственным за направление или лидером команды
        is_responsible = VolunteerDirection.objects.filter(responsible=volunteer).exists()
        is_leader = Command.objects.filter(leader=volunteer).exists()
        
        if is_responsible or is_leader:
            # Если был обычным волонтером -> повышаем до куратора и даем доступ в админку
            if volunteer.role == 'volunteer':
                volunteer.role = 'curator'
                volunteer.is_staff = True
                volunteer.save()
            # Если уже был тимлидом/админом, но не имел staff статуса -> даем доступ
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
    queryset = ActivitySubmission.objects.all()
    serializer_class = ActivitySubmissionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        # Оптимизация: select_related для уменьшения запросов при сериализации task
        return ActivitySubmission.objects.filter(volunteer=self.request.user).select_related('task').order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(volunteer=self.request.user)


class DiscoveryListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        all_directions = VolunteerDirection.objects.all()
        
        # Исправляем обращение к командам
        user_commands = user.volunteer_commands.all() 
        user_directions = user.direction.all()

        tasks = ActivityTask.objects.filter(
            Q(command__isnull=True) |   
            Q(command__in=user_commands) 
        ).select_related('command').distinct()

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
        qs = ActivitySubmission.objects.select_related('task', 'volunteer', 'task__command')

        if user.is_superuser or user.role == 'admin':
            return qs.order_by('-created_at')
            
        # Логика Куратора:
        return qs.filter(
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
        # Показываем анкеты, где пользователь является лидером команд, выбранных в анкете
        return VolunteerApplication.objects.filter(
            commands__leader=user
        ).distinct()

    def perform_create(self, serializer):
        user = self.request.user
        data = serializer.validated_data

        # 🚫 VolunteerApplication НЕ СОЗДАЁМ
        # Просто игнорируем эту модель

        # --- Обновляем ТОЛЬКО Volunteer ---
        if 'full_name' in data:
            user.name = data['full_name']

        if 'phone_number' in data:
            user.phone_number = data['phone_number']

        if 'email' in data:
            user.email = data['email']

        if 'direction' in data and data['direction']:
            user.direction.set([data['direction']])

        if 'commands' in data:
            user.volunteer_commands.set(data['commands'])

        # Проверяем роль
        is_responsible = VolunteerDirection.objects.filter(responsible=user).exists()
        is_leader = Command.objects.filter(leader=user).exists()

        if is_responsible or is_leader:
            user.role = 'curator'
            user.is_staff = True

        user.save()


class VolunteerListView(generics.ListAPIView):
    serializer_class = VolunteerListSerializer  
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Volunteer.objects.prefetch_related('direction')

        # 1. Если Админ — просто возвращаем всех с базовыми баллами
        if user.is_superuser or user.role == 'admin':
            return qs.annotate(
                yellow_card_count=Count('yellow_cards', distinct=True),
                # Используем Value(0), если local_points пока не критичны
                local_points=Coalesce('point', Value(0), output_field=DecimalField())
            )

        # 2. Логика Куратора/Тимлида (упрощенная)
        my_directions = VolunteerDirection.objects.filter(responsible=user)
        my_commands = Command.objects.filter(leader=user)

        # Фильтруем волонтеров, которые относятся к куратору
        queryset = qs.filter(
            Q(direction__in=my_directions) | 
            Q(volunteer_commands__in=my_commands) # Используем исправленный related_name
        ).distinct()

        # 3. Базовая аннотация без сложных Sum
        queryset = queryset.annotate(
            yellow_card_count=Count('yellow_cards', distinct=True),
            local_points=Value(0, output_field=DecimalField()) # Временно обнуляем для теста
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

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Volunteer, Attendance
from .serializers import BulkAttendanceSerializer
from django.db import transaction

class AttendanceViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    # 1. ПОЛУЧЕНИЕ ЖУРНАЛА
    @action(detail=False, methods=['get'])
    def month_journal(self, request):
        direction_id = request.query_params.get('direction_id')
        month_str = request.query_params.get('month') # "YYYY-MM"
        
        if not direction_id or not month_str:
            return Response({"error": "Нужны direction_id и month"}, status=400)

        try:
            year, month = map(int, month_str.split('-'))
        except ValueError:
            return Response({"error": "Неверный формат даты"}, status=400)

        # --- ИЗМЕНЕНИЕ ЗДЕСЬ ---
        # Фильтруем: только те, у кого role='volunteer'
        volunteers = Volunteer.objects.filter(
            direction__id=direction_id, 
            role='volunteer'
        ).order_by('name')
        # -----------------------
        
        # Получаем записи посещаемости
        logs = Attendance.objects.filter(
            direction_id=direction_id,
            date__year=year,
            date__month=month
        ).order_by('date')

        existing_dates = sorted(list(set([log.date.strftime('%Y-%m-%d') for log in logs])))

        journal_map = {}
        for log in logs:
            vid = log.volunteer_id
            d_str = log.date.strftime('%Y-%m-%d')
            if vid not in journal_map: journal_map[vid] = {}
            journal_map[vid][d_str] = log.status

        vol_list = []
        for vol in volunteers:
            name = vol.name or vol.login
            parts = name.split()
            initials = (parts[0][0] + (parts[1][0] if len(parts)>1 else "")).upper()[:2]
            
            vol_list.append({
                "id": vol.id,
                "name": name,
                "initials": initials,
                "records": journal_map.get(vol.id, {})
            })
            
        return Response({
            "dates": existing_dates,
            "volunteers": vol_list
        })

    # 2. СОХРАНЕНИЕ
    @action(detail=False, methods=['post'])
    def mark_bulk(self, request):
        data = request.data
        direction_id = data.get('direction_id')
        records = data.get('records', [])

        # Проверка прав (кто может отмечать)
        if request.user.role not in ['bailiff_activity', 'admin', 'curator', 'president']:
            return Response({"error": "Нет прав"}, status=403)

        saved_count = 0
        with transaction.atomic():
            for item in records:
                date_str = item.get('date')
                vol_id = item.get('volunteer_id')
                status = item.get('status')

                if not date_str or not vol_id: continue

                if not status: 
                    Attendance.objects.filter(
                        volunteer_id=vol_id, direction_id=direction_id, date=date_str
                    ).delete()
                else:
                    Attendance.objects.update_or_create(
                        volunteer_id=vol_id, direction_id=direction_id, date=date_str,
                        defaults={'status': status, 'marked_by': request.user}
                    )
                saved_count += 1
            
        return Response({"message": "Сохранено"})
    
class BailiffPanelView(TemplateView):
    template_name = "volunteers/bailiff_panel.html"

class EquityViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    # 1. Получение списка (Таблица)
    @action(detail=False, methods=['get'])
    def board(self, request):
        direction_id = request.query_params.get('direction_id')
        if not direction_id:
            return Response({"error": "Нужен direction_id"}, status=400)

        # Берем только волонтеров (фильтр role='volunteer')
        volunteers = Volunteer.objects.filter(
            direction__id=direction_id, 
            role='volunteer'
        ).order_by('name')

        data = []
        for vol in volunteers:
            # Получаем все карточки волонтера
            cards = YellowCard.objects.filter(volunteer=vol).order_by('date_issued')
            card_data = [{"id": c.id, "date": c.date_issued, "reason": c.reason} for c in cards]
            
            data.append({
                "id": vol.id,
                "name": vol.name or vol.login,
                "cards": card_data, # Список карточек
                "count": len(card_data)
            })

        return Response(data)

    # 2. Выдать/Убрать карточку
    @action(detail=False, methods=['post'])
    def toggle_card(self, request):
        # Проверка прав (Equity officer, Admin, Curator)
        if request.user.role not in ['equity_officer', 'admin', 'curator', 'president']:
             return Response({"error": "Нет прав"}, status=403)

        vol_id = request.data.get('volunteer_id')
        action_type = request.data.get('action') # 'add' или 'remove'

        try:
            volunteer = Volunteer.objects.get(id=vol_id)
        except Volunteer.DoesNotExist:
            return Response({"error": "Волонтер не найден"}, status=404)

        current_count = YellowCard.objects.filter(volunteer=volunteer).count()

        if action_type == 'add':
            if current_count >= 4:
                return Response({"error": "Максимум 4 карточки!"}, status=400)
            
            YellowCard.objects.create(
                volunteer=volunteer,
                issued_by=request.user,
                reason=request.data.get('reason', 'Нарушение')
            )
            return Response({"message": "Карточка выдана", "new_count": current_count + 1})

        elif action_type == 'remove':
            if current_count == 0:
                return Response({"error": "У волонтера нет карточек"}, status=400)
            
            # Удаляем последнюю выданную карточку
            last_card = YellowCard.objects.filter(volunteer=volunteer).last()
            if last_card:
                last_card.delete()
            
            return Response({"message": "Карточка снята", "new_count": current_count - 1})

        return Response({"error": "Неверное действие"}, status=400)
    
class EquityPanelView(TemplateView):
    template_name = "volunteers/equity_panel.html"
# ---------------- PDF ГЕНЕРАЦИЯ (С кириллицей) ----------------

class DownloadPDFBase(APIView):
    permission_classes = [AllowAny]

    def get_pdf_response(self, volunteers, title, filename):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        
        # Подключение шрифта с поддержкой кириллицы
        font_path = os.path.join(settings.BASE_DIR, 'FreeSans.ttf')
        font_name = 'FreeSans' if os.path.exists(font_path) else 'Helvetica'
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('FreeSans', font_path))

        elements.append(Paragraph(title, ParagraphStyle('T', fontName=font_name, fontSize=18, alignment=1)))
        
        data = [['№', 'ФИО', 'Телефон']]
        for i, v in enumerate(volunteers):
            # Проверка на None, чтобы не упало при генерации
            name = v.full_name if v.full_name else "Не указано"
            phone = v.phone_number if v.phone_number else "-"
            data.append([str(i+1), name, phone])
        
        t = Table(data, colWidths=[30, 300, 150])
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), font_name),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
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
        # API для Канбан-доски (возвращает списки по статусам)
        from .models import VolunteerApplication
        
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