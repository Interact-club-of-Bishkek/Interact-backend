import io
import os
from unicodedata import decimal
from django.db import transaction
from django.conf import settings
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from langchain_core.documents import Document
from projects.models import Project  
from langchain.prompts import PromptTemplate
from django.utils import timezone
# <-- Проверь, правильный ли путь до твоей модели проектов!
# ВАЖНО: Импортируем DecimalField именно отсюда для ORM
# Найди эту строку (примерно в начале файла)
from django.db.models import Sum, Value, Q, DecimalField, Count, F  # <--- ДОБАВЬ 'F' СЮДА
from django.db.models.functions import Coalesce

from rest_framework import viewsets, generics, status, permissions
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from langchain_community.document_loaders import PyPDFLoader
from langchain_groq import ChatGroq
from langchain.chains.question_answering import load_qa_chain
# ReportLab для генерации PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from rest_framework.decorators import api_view, permission_classes

# Импорты моделей (лучше держать их вверху, если нет циклической зависимости)
from .models import (
    AppSettings, Attendance, Volunteer, VolunteerApplication, BotAccessConfig, 
    ActivityTask, ActivitySubmission, YellowCard, ChatSession, ChatMessage
)
from directions.models import VolunteerDirection
from commands.models import Command

from .serializers import (
    BulkAttendanceSerializer, VolunteerSerializer, VolunteerLoginSerializer, VolunteerRegisterSerializer,
    VolunteerApplicationSerializer, ActivityTaskSerializer, 
    ActivitySubmissionSerializer, VolunteerDirectionSerializer, CommandSerializer,
    VolunteerListSerializer
)
from decimal import Decimal

# ---------------- АВТОРИЗАЦИЯ И ПРОФИЛЬ ----------------



class VolunteerLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VolunteerLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        volunteer = serializer.validated_data.get("user") or serializer.validated_data.get("volunteer")
        
        # --- ОБНОВЛЕНИЕ РОЛИ ПЕРЕД ОТВЕТОМ ---
        is_responsible = VolunteerDirection.objects.filter(responsible=volunteer).exists()
        is_leader = Command.objects.filter(leader=volunteer).exists()
        
        if is_responsible or is_leader:
            if volunteer.role == 'volunteer':
                volunteer.role = 'curator'
                volunteer.is_staff = True
                volunteer.save()
            elif not volunteer.is_staff:
                volunteer.is_staff = True
                volunteer.save()
        # -------------------------------------

        refresh = RefreshToken.for_user(volunteer)
        
        # === ИСПРАВЛЕНИЕ ЗДЕСЬ ===
        # Было: volunteer.commands.exists() -> Ошибка
        # Стало: volunteer.volunteer_commands.exists()
        is_assigned = volunteer.direction.exists() or volunteer.volunteer_commands.exists()
        
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
        # Больше ничего считать не надо, сериализатор сделает это сам
        return self.request.user



# ---------------- ЛИЧНЫЙ КАБИНЕТ ВОЛОНТЕРА ----------------

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def volunteer_direction_preferences(request):
    settings = AppSettings.get_settings()
    
    # Метод GET: проверить, открыт ли набор и что уже выбрано
    if request.method == 'GET':
        return Response({
            "is_open": settings.is_direction_selection_open,
            "preferred": list(request.user.preferred_directions.values_list('id', flat=True))
        })

    # Метод POST: сохранить 3 направления
    if not settings.is_direction_selection_open:
        return Response({"error": "Выбор направлений сейчас закрыт."}, status=403)

    direction_ids = request.data.get('directions', [])
    
    if len(direction_ids) > 3:
        return Response({"error": "Можно выбрать максимум 3 направления."}, status=400)

    # Проверяем, существуют ли такие направления
    valid_ids = VolunteerDirection.objects.filter(id__in=direction_ids).values_list('id', flat=True)
    
    # Сохраняем в базу
    request.user.preferred_directions.set(valid_ids)
    
    return Response({"message": "Ваши предпочтения успешно сохранены!", "saved": valid_ids})

class VolunteerActivityViewSet(viewsets.ModelViewSet):
    queryset = ActivitySubmission.objects.all()
    serializer_class = ActivitySubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ActivitySubmission.objects.filter(volunteer=self.request.user).select_related('task').order_by('-created_at')

    def perform_create(self, serializer):
        command_id = self.request.data.get('command')
        direction_id = self.request.data.get('direction')
        
        # 🔥 2. ВЫТАСКИВАЕМ QUANTITY НАПРЯМУЮ ИЗ JSON ОТ ФРОНТЕНДА
        quantity = self.request.data.get('quantity', 1)

        instance = serializer.save(
            volunteer=self.request.user,
            command_id=command_id,
            direction_id=direction_id,
            quantity=quantity  # 🔥 3. ЖЕСТКО ЗАПИСЫВАЕМ ЕГО В БАЗУ ДАННЫХ
        )
        if instance.command and not instance.direction:
            instance.direction = instance.command.direction
            instance.save()
    # ДОБАВЬ ЭТОТ МЕТОД:
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != 'pending':
            return Response(
                {"error": "Можно отменить только заявки, которые находятся в ожидании."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

from decimal import Decimal, InvalidOperation # Добавьте в импорты вверху

class DeductPointsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Проверяем права: админ, куратор или лидер команды
        is_leader = Command.objects.filter(leader=request.user).exists()
        if request.user.role not in ['admin', 'curator', 'president'] and not is_leader:
            return Response({"error": "Нет прав для начисления штрафов"}, status=status.HTTP_403_FORBIDDEN)

        vol_id = request.data.get('volunteer_id')
        raw_points = request.data.get('points', 0)
        reason = request.data.get('reason', 'Штраф')

        try:
            # Преобразуем в Decimal, чтобы Django не ругался на float
            points_to_deduct = Decimal(str(raw_points))
        except (ValueError, TypeError, InvalidOperation):
            return Response({"error": "Некорректная сумма баллов"}, status=status.HTTP_400_BAD_REQUEST)

        if points_to_deduct <= 0:
            return Response({"error": "Сумма штрафа должна быть больше нуля"}, status=status.HTTP_400_BAD_REQUEST)

        volunteer = get_object_or_404(Volunteer, id=vol_id)
        
        with transaction.atomic():
            # Создаем или находим системное задание для штрафов
            task, _ = ActivityTask.objects.get_or_create(
                title="⚠️ Штраф / Списание баллов",
                defaults={'points': 0, 'is_flexible': True}
            )
            
            # Создаем запись. Отрицательное число автоматически уменьшит баланс через сигнал
            ActivitySubmission.objects.create(
                volunteer=volunteer,
                task=task,
                status='approved',
                points_awarded=-points_to_deduct, 
                description=f"Списание: {reason}",
                # Если передан ID команды, привязываем штраф к ней
                command_id=request.data.get('command_id') 
            )
            
        return Response({"status": "success", "message": "Баллы успешно списаны"})

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
        uid = user.id
        
        qs = ActivitySubmission.objects.select_related(
            'task', 'volunteer', 'command', 'direction'
        ).prefetch_related('volunteer__direction')

        if user.is_superuser or user.role == 'admin':
            return qs.order_by('-created_at')

        # 1. Тимлид команды: видит все заявки своей команды (новые и старые)
        is_team_leader = Q(command__leader_id=uid)

        # 2. Куратор направления: 
        # Видит "чистые" заявки направления (где команда НЕ выбрана)
        is_direction_curator = Q(direction__responsible_id=uid, command__isnull=True)

        # 3. Контроль для куратора: 
        # Видит командные заявки своего направления ТОЛЬКО если они уже ОДОБРЕНЫ тимлидом
        is_overseer = Q(command__direction__responsible_id=uid, status='approved')

        return qs.filter(
            is_team_leader | is_direction_curator | is_overseer
        ).distinct().order_by('-created_at')

    def perform_update(self, serializer):
            # Просто сохраняем. Пересчет баллов автоматически сделает сигнал из models.py!
            serializer.save()
    
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
        managed_commands = Command.objects.filter(Q(leader=user) | Q(direction__responsible=user))
        qs = Volunteer.objects.prefetch_related('direction', 'volunteer_commands')

        qs = qs.annotate(
            # Считаем ВСЕ баллы волонтера по истории (points_awarded ИЛИ task__points * quantity)
            calculated_total=Coalesce(
                Sum(
                    Coalesce(
                        'submissions__points_awarded', 
                        F('submissions__task__points') * F('submissions__quantity'), # <--- ЗДЕСЬ ИЗМЕНЕНИЕ
                        output_field=DecimalField()
                    ), 
                    filter=Q(submissions__status='approved')
                ),
                Value(0),
                output_field=DecimalField()
            ),
            # Считаем баллы в твоих командах
            local_points=Coalesce(
                Sum(
                    Coalesce(
                        'submissions__points_awarded', 
                        F('submissions__task__points') * F('submissions__quantity'), # <--- И ЗДЕСЬ ИЗМЕНЕНИЕ
                        output_field=DecimalField()
                    ), 
                    filter=Q(submissions__command__in=managed_commands, submissions__status='approved')
                ), 
                Value(0), 
                output_field=DecimalField()
            ),
            yellow_card_count=Count('yellow_cards', distinct=True)
        )
        return qs.order_by('name')


# --- НОВЫЙ КЛАСС ДЛЯ УДАЛЕНИЯ ---
class RemoveVolunteerFromCommandView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        # pk - это ID команды
        command = get_object_or_404(Command, pk=pk)
        
        # Проверка прав: удалять может только лидер этой команды или админ
        if command.leader != request.user and not request.user.is_superuser:
            return Response({"error": "Нет прав"}, status=status.HTTP_403_FORBIDDEN)

        vol_id = request.data.get('volunteer_id')
        if not vol_id:
            return Response({"error": "ID волонтера не передан"}, status=status.HTTP_400_BAD_REQUEST)

        volunteer = get_object_or_404(Volunteer, pk=vol_id)
        
        # Удаляем связь
        command.volunteers.remove(volunteer)
        
        return Response({"status": "success", "message": f"{volunteer.name} удален из команды"})


class VolunteerViewSet(viewsets.ModelViewSet):
    serializer_class = VolunteerSerializer
    permission_classes = [IsAuthenticated]
    queryset = Volunteer.objects.all()

    def get_queryset(self):
        user = self.request.user
        # Проверяем, является ли он лидером хотя бы одной команды
        is_leader = Command.objects.filter(leader=user).exists()
        
        if user.is_staff or user.role in ['admin', 'curator'] or is_leader:
            return Volunteer.objects.all().order_by('-date_joined')
        
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

    # 1. ПОЛУЧЕНИЕ ЖУРНАЛА (Осталось без изменений)
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

        # Фильтруем: только те, у кого role='volunteer'
        volunteers = Volunteer.objects.filter(
            direction__id=direction_id, 
            role='volunteer'
        ).order_by('name')
        
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

    # 2. СОХРАНЕНИЕ (Осталось без изменений)
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

    # 3. НОВЫЙ ЭНДПОИНТ: СТАТИСТИКА И РЕЙТИНГ ЗА МЕСЯЦ
    @action(detail=False, methods=['get'])
    def stats_by_month(self, request):
        # Получаем все направления
        directions = VolunteerDirection.objects.all()
        data = []

        for current_dir in directions:
            # СЧИТАЕМ БАЛЛЫ ИДЕАЛЬНО: с учетом умножения на quantity
            # Добавили предварительную подгрузку, чтобы не грузить БД (Оптимизация)
            vols = Volunteer.objects.filter(
                direction=current_dir, 
                role='volunteer'
            ).annotate(
                total_score=Coalesce(
                    Sum(
                        Coalesce(
                            'submissions__points_awarded', 
                            F('submissions__task__points') * F('submissions__quantity'),
                            output_field=DecimalField()
                        ), 
                        filter=Q(submissions__status='approved')
                    ),
                    Value(0),
                    output_field=DecimalField()
                )
            ).prefetch_related(
                'submissions', 
                'submissions__task',
                'submissions__command',
                'submissions__direction'
            )

            vol_list = []
            for v in vols:
                # 1. Берем ИДЕАЛЬНУЮ сумму, которую посчитала база данных
                score = float(v.total_score)

                # 2. Собираем список заданий для всплывающего окна (модалки)
                approved_subs = [s for s in v.submissions.all() if s.status == 'approved']
                tasks_data = []
                for sub in approved_subs:
                    # Учитываем quantity и для модалки рейтинга
                    qty = getattr(sub, 'quantity', 1) # На всякий случай безопасно получаем quantity
                    
                    if sub.points_awarded is not None:
                        p = float(sub.points_awarded)
                    else:
                        p = float(sub.task.points) * qty if sub.task else 0.0

                    # 🔥 ИСПРАВЛЕНИЕ: ДОБАВЛЕНЫ ВСЕ НЕОБХОДИМЫЕ ДАННЫЕ В JSON
                    tasks_data.append({
                        "title": sub.task.title if sub.task else "Без названия",
                        "points": p,
                        "date": sub.created_at.strftime('%Y-%m-%d'),
                        "description": sub.description,
                        "command_title": sub.command.title if sub.command else None,
                        "direction_name": sub.direction.name if sub.direction else None,
                        "quantity": qty
                    })

                vol_list.append({
                    "id": v.id,
                    "name": v.name or v.login,
                    "score": score,
                    "tasks": tasks_data
                })

            # Оставляем только те направления, где есть волонтеры
            if vol_list:
                data.append({
                    "direction_id": current_dir.id,
                    "direction_name": current_dir.name,
                    "volunteers": vol_list
                })

        return Response(data)
    
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

# ==========================================
# ЛОГИКА ПРИСТАВА БАЗ (РАСПРЕДЕЛЕНИЕ)
# ==========================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_auto_distribution(request):
    """Генерирует черновик равномерного распределения на основе предпочтений."""
    # Проверка прав
    if request.user.role not in ['bailiff_base', 'admin', 'president']:
        return Response({"error": "Нет прав"}, status=403)

    volunteers = list(Volunteer.objects.filter(is_active=True, role='volunteer').prefetch_related('preferred_directions'))
    directions = list(VolunteerDirection.objects.all())
    
    if not directions:
        return Response({"error": "Нет направлений в базе"}, status=400)

    # Целевое количество людей в 1 направлении (округляем в большую сторону)
    target_capacity = (len(volunteers) // len(directions)) + 1 
    
    distribution_result = []
    direction_counts = {d.id: 0 for d in directions}
    
    import random
    random.shuffle(volunteers)

    for vol in volunteers:
        prefs = list(vol.preferred_directions.values_list('id', flat=True))
        assigned_dir_id = None
        
        # 1. Пытаемся засунуть в одно из желаемых направлений
        for pref_id in prefs:
            if direction_counts.get(pref_id, 0) < target_capacity:
                assigned_dir_id = pref_id
                break
        
        # 2. Если все желаемые уже забиты битком, кидаем в самое пустое
        if not assigned_dir_id:
            emptiest_dir_id = min(direction_counts, key=direction_counts.get)
            assigned_dir_id = emptiest_dir_id

        direction_counts[assigned_dir_id] += 1
        distribution_result.append({
            "volunteer_id": vol.id,
            "volunteer_name": vol.name or vol.login,
            "assigned_direction_id": assigned_dir_id
        })

    return Response({"distribution": distribution_result, "counts": direction_counts})

@api_view(['GET'])
@permission_classes([AllowAny]) # Доступно всем, даже без токена
def get_app_settings(request):
    settings = AppSettings.get_settings()
    return Response({
        "is_registration_open": settings.is_registration_open,
        "is_direction_selection_open": settings.is_direction_selection_open
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def ai_pdf_chat(request):
    user_text = request.data.get('message')
    session_id = request.data.get('session_id')

    if not user_text or not session_id:
        return Response({"error": "Пустое сообщение или нет сессии"}, status=400)

    # 1. Сохраняем сообщение
    session, _ = ChatSession.objects.get_or_create(session_id=session_id)
    ChatMessage.objects.create(session=session, sender='user', text=user_text)

    try:
        # 2. Грузим статичный PDF
        pdf_path = os.path.join(settings.BASE_DIR, 'rules.pdf')
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()

        # ==========================================
        # 3. ДОБАВЛЯЕМ ДИНАМИКУ ИЗ БД
        # ==========================================
        # Убрали time_start__gte=now, чтобы пока выводились ВСЕ неархивные проекты
        active_projects = Project.objects.filter(is_archived=False).order_by('-time_start')[:5] 
        
        if active_projects.exists():
            projects_info = "=== АКТУАЛЬНЫЕ ПРОЕКТЫ ИЗ БАЗЫ ДАННЫХ: ===\n"
            for p in active_projects:
                date_str = p.time_start.strftime("%d.%m.%Y") if p.time_start else "Скоро"
                projects_info += f"- [{p.name}](/projects/{p.slug}/) (Дата: {date_str}, Категория: {p.get_category_display()})\n"
        else:
            projects_info = "=== АКТУАЛЬНЫЕ ПРОЕКТЫ ===\nВ данный момент активных проектов нет."

        dynamic_doc = Document(
            page_content=projects_info,
            metadata={"source": "database_recent_projects"}
        )
        documents.append(dynamic_doc)
        # ==========================================

        # Извлекаем ключ из переменных окружения
        groq_api_key = os.environ.get("GROQ_API_KEY")

        # Инициализируем модель через твой прокси-мост
        llm = ChatGroq(
            api_key=groq_api_key,
            model_name="llama-3.1-8b-instant", 
            temperature=0.3,
            # Указываем путь к твоему воркеру
            # Добавляем /openai/v1, чтобы LangChain нашел нужные эндпоинты
            base_url="https://icy-dust-9f56.mamadalievmaruf740.workers.dev/openai/v1"
        )
        # === ИДЕАЛЬНЫЙ СБАЛАНСИРОВАННЫЙ ПРОМПТ ===
        prompt_template = """Ты — дружелюбный и современный ИИ-помощник Interact Club of Bishkek.
        Опираясь на предоставленный контекст, ответь на вопрос пользователя.

        ТВОИ СТРОГИЕ ПРАВИЛА:
        1. КРАСОТА: Отвечай очень красиво и структурированно. Обязательно используй абзацы, списки (с тире) и все возможные эмодзи подходящиеся по смыслу.
        2. О КЛУБЕ: Если спрашивают "кто вы", "правила" или историю — бери информацию  из PDF-файла в контексте.
        3. ПРОЕКТЫ: Если просят показать проекты, бери информацию ТОЛЬКО из раздела "АКТУАЛЬНЫЕ ПРОЕКТЫ ИЗ БАЗЫ ДАННЫХ".
        4. ССЫЛКИ: КАТЕГОРИЧЕСКИ ЗАПРЕЩАЕТСЯ придумывать свои ссылки. Выводи проекты ровно в том формате, в котором они переданы (с синтаксисом Markdown).

        Контекст:
        {context}

        Вопрос: {question}
        Красивый ответ:"""

        PROMPT = PromptTemplate(
            template=prompt_template, input_variables=["context", "question"]
        )
        
        chain = load_qa_chain(llm, chain_type="stuff", prompt=PROMPT)
        result = chain.invoke({"input_documents": documents, "question": user_text})
        answer = result["output_text"]

        # 6. Сохраняем ответ ИИ
        ChatMessage.objects.create(session=session, sender='ai', text=answer)

        return Response({"answer": answer})

    except Exception as e:
        error_msg = f"Ошибка ИИ: {str(e)}"
        print(f"🔴 ТОЧНАЯ ОШИБКА ДЛЯ ДЕБАГА: {e}")
        ChatMessage.objects.create(session=session, sender='ai', text=error_msg)
        return Response({"error": error_msg}, status=500)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def apply_distribution(request):
    """Отдает черновик или применяет финальное распределение."""
    if request.user.role not in ['bailiff_base', 'admin', 'president']:
        return Response({"error": "Нет прав"}, status=403)

    # --- 1. ОТДАЕМ ДАННЫЕ (Чтение) ---
    if request.method == 'GET':
        volunteers = Volunteer.objects.filter(is_active=True, role='volunteer')
        dist = []
        for vol in volunteers:
            # Если у волонтера есть сохраненный черновик — показываем его на доске.
            # Если черновика нет — показываем его текущее РЕАЛЬНОЕ направление.
            if vol.draft_direction:
                dir_id = vol.draft_direction.id
            else:
                dir_id = vol.direction.first().id if vol.direction.exists() else ''
                
            dist.append({
                "volunteer_id": vol.id,
                "volunteer_name": vol.name or vol.login,
                "assigned_direction_id": dir_id
            })
        return Response({"distribution": dist})

    # --- 2. СОХРАНЯЕМ ДАННЫЕ (Запись) ---
    action = request.data.get('action') 
    mapping = request.data.get('mapping', [])

    if action not in ['save_only', 'distribute_and_reset']:
        return Response({"error": "Неизвестное действие"}, status=400)

    with transaction.atomic():
        for item in mapping:
            vol_id = item.get('vol_id')
            dir_id = item.get('dir_id')
            
            try:
                vol = Volunteer.objects.get(id=vol_id)
            except Volunteer.DoesNotExist:
                continue

            # ДЕЙСТВИЕ 1: ТОЛЬКО СОХРАНИТЬ ЧЕРНОВИК
            if action == 'save_only':
                vol.draft_direction_id = dir_id if dir_id else None
                vol.save()
                
            # ДЕЙСТВИЕ 2: ПРИМЕНИТЬ ОКОНЧАТЕЛЬНО И СБРОСИТЬ
            elif action == 'distribute_and_reset':
                # 1. Меняем РЕАЛЬНОЕ направление
                vol.direction.clear()
                if dir_id:
                    vol.direction.add(dir_id)
                
                # 2. Очищаем черновик за ненадобностью
                vol.draft_direction = None

                # 3. ЖЕСТКИЙ СБРОС СЕЗОНА
                vol.point = 0
                vol.yellow_card = 0
                vol.preferred_directions.clear() 
                vol.submissions.all().delete() 
                vol.save()
                
    if action == 'distribute_and_reset':
        settings = AppSettings.get_settings()
        settings.is_direction_selection_open = False
        settings.save()

    return Response({"message": f"Успешно выполнено: {action}"})

class CuratorPanelView(TemplateView): template_name = "volunteers/curator_panel.html"
class VolunteerCabinetView(TemplateView): template_name = "volunteers/volunteer_cabinet.html"
class BailiffBasePanelView(TemplateView): template_name = "volunteers/bailiff_base_panel.html"
class LoginPageView(TemplateView): template_name = "volunteers/login.html"
class VolunteerBoardView(TemplateView): template_name = "volunteers/columns.html"