import io
import os
import random
import string
import math
from datetime import datetime, timedelta

from django.db import transaction
from django.conf import settings
from django.core.mail import send_mail
from django.http import FileResponse
from django.views.generic import TemplateView

from rest_framework import viewsets, generics, status, serializers
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken

# ReportLab для генерации красивого PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .models import Volunteer, VolunteerApplication, BotAccessConfig
from .serializers import (
    VolunteerSerializer, VolunteerLoginSerializer,
    VolunteerApplicationSerializer, VolunteerApplicationStatusUpdateSerializer, BotAuthSerializer
)

# ---------------- Volunteers ----------------
class VolunteerViewSet(viewsets.ModelViewSet):
    queryset = Volunteer.objects.all()
    serializer_class = VolunteerSerializer


class VolunteerLoginView(APIView):
    permission_classes = []  # логин доступен без токена

    def post(self, request):
        serializer = VolunteerLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        volunteer = serializer.validated_data["volunteer"]

        refresh = RefreshToken.for_user(volunteer)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "volunteer": {
                "id": volunteer.id,
                "name": volunteer.name,
                "login": volunteer.login,
                "board": volunteer.board,
            }
        })


class VolunteerProfileView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = VolunteerSerializer

    def get_object(self):
        return Volunteer.objects.get(id=self.request.user.id)


# ---------------- Serializers для колонок ----------------

class VolunteerColumnsSerializer(serializers.Serializer):
    """
    Сериализатор для объединения заявок по статусам.
    Используем VolunteerApplicationSerializer для всех статусов, 
    чтобы на фронте были доступны все данные анкеты.
    """
    submitted = VolunteerApplicationSerializer(many=True, read_only=True)
    interview = VolunteerApplicationSerializer(many=True, read_only=True)
    accepted = VolunteerApplicationSerializer(many=True, read_only=True)


# ---------------- Volunteer Applications ----------------
class VolunteerApplicationViewSet(viewsets.ModelViewSet):
    queryset = VolunteerApplication.objects.all().order_by('-created_at')
    serializer_class = VolunteerApplicationSerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        obj = self.get_object()
        serializer = VolunteerApplicationStatusUpdateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        status_new = serializer.validated_data.get('status')

        creating_volunteer = False
        if status_new == 'accepted' and not obj.volunteer_created:
            creating_volunteer = True

        serializer.save()

        if creating_volunteer:
            with transaction.atomic():
                # Создаем запись волонтера на основе анкеты
                volunteer = Volunteer.objects.create(
                    name=obj.full_name,
                    phone_number=obj.phone_number,
                    email=obj.email,
                    image=obj.photo 
                )
                
                if obj.directions.exists():
                    volunteer.direction.set(obj.directions.all())
                
                obj.volunteer_created = True
                obj.volunteer = volunteer
                obj.save()

        return Response({'status': 'updated', 'new_status': obj.status})

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def send_credentials(self, request):
        applications = VolunteerApplication.objects.filter(
            status='accepted',
            volunteer_created=True
        )

        if not applications.exists():
            return Response({'detail': 'Нет новых принятых волонтёров'}, status=status.HTTP_404_NOT_FOUND)

        sent = []
        for app in applications:
            volunteer = getattr(app, 'volunteer', None)
            if not volunteer:
                continue

            password = volunteer.visible_password or ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            if not volunteer.visible_password:
                volunteer.set_password(password)
                volunteer.visible_password = password
                volunteer.save()

            send_mail(
                subject='Ваши данные для входа в систему волонтёра',
                message=f"Здравствуйте {volunteer.name}!\n\nВаш логин: {volunteer.login}\nВаш пароль: {password}\n\nС уважением, команда Interact Club.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[volunteer.email],
                fail_silently=False,
            )
            sent.append(volunteer.email)

        return Response({'sent_to': sent, 'count': len(sent)})


# ---------------- Columns View ----------------

class VolunteerColumnsView(APIView):
    """
    GET: возвращает группы волонтеров (анкеты) для Канбан-доски
    """
    permission_classes = [] 

    def get(self, request):
        submitted = VolunteerApplication.objects.filter(status='submitted').order_by('-created_at')
        interview = VolunteerApplication.objects.filter(status='interview').order_by('-created_at')
        accepted = VolunteerApplication.objects.filter(status='accepted').order_by('-created_at')
        
        context = {'request': request} 
        serializer = VolunteerColumnsSerializer(
            {
                'submitted': submitted,
                'interview': interview,
                'accepted': accepted
            }, 
            context=context 
        )
        return Response(serializer.data)


class SendAcceptedVolunteersEmailsView(APIView):
    permission_classes = []

    def post(self, request):
        applications = VolunteerApplication.objects.filter(
            status='accepted',
            volunteer_created=True
        ).select_related('volunteer')

        if not applications.exists():
            return Response({'detail': 'Нет принятых волонтёров для отправки'}, status=status.HTTP_404_NOT_FOUND)

        sent = []
        failed = []

        for app in applications:
            volunteer = getattr(app, 'volunteer', None)
            if not volunteer or not volunteer.email:
                continue

            password = volunteer.visible_password or ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            if not volunteer.visible_password:
                volunteer.set_password(password)
                volunteer.visible_password = password
                volunteer.save()

            try:
                send_mail(
                    subject='Ваши данные для входа в систему волонтёра',
                    message=(
                        f"Здравствуйте {volunteer.name}!\n\n"
                        f"Ваш логин: {volunteer.login}\n"
                        f"Ваш пароль: {password}\n\n"
                        "С уважением, команда Interact Club."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[volunteer.email],
                    fail_silently=False,
                )
                sent.append(volunteer.email)
            except Exception as e:
                failed.append({'email': volunteer.email, 'error': str(e)})
                continue

        return Response({
            'sent_to': sent,
            'failed': failed,
            'count_sent': len(sent),
            'count_failed': len(failed)
        })


# ---------------- Bot Auth ----------------

class BotCheckAccessView(APIView):
    permission_classes = [] 

    def post(self, request):
        serializer = BotAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        access_type = serializer.validated_data['access_type']
        password = serializer.validated_data['password']

        configs = {config.role: config.password for config in BotAccessConfig.objects.all()}
        
        curator_pass = configs.get('curator')
        volunteer_pass = configs.get('volunteer')

        if password == curator_pass:
            return Response({"status": "access_granted", "role": "curator"}, status=status.HTTP_200_OK)

        if access_type == "commands" and password == volunteer_pass:
            return Response({"status": "access_granted", "role": "volunteer"}, status=status.HTTP_200_OK)

        return Response({"status": "access_denied"}, status=status.HTTP_403_FORBIDDEN)


# ---------------- PDF Генерация ----------------

class DownloadInterviewScheduleView(APIView):
    permission_classes = []

    def get(self, request):
        try:
            volunteers_query = VolunteerApplication.objects.filter(status='interview').order_by('full_name')
            volunteers_list = list(volunteers_query)
            num_volunteers = len(volunteers_list)
            
            if num_volunteers == 0:
                return Response({"error": "Список волонтеров пуст"}, status=400)

            buffer = io.BytesIO()
            # Увеличим отступы, чтобы таблица точно влезла
            doc = SimpleDocTemplate(
                buffer, 
                pagesize=A4,
                rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30
            )
            elements = []

            # --- ШРИФТ ---
            font_name = 'Helvetica'
            font_path = os.path.join(settings.BASE_DIR, 'FreeSans.ttf')
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('FreeSans', font_path))
                    font_name = 'FreeSans'
                except: pass

            title_style = ParagraphStyle(
                'TitleStyle', fontName=font_name, fontSize=18,
                alignment=1, textColor=colors.HexColor("#333333"), spaceAfter=20
            )
            elements.append(Paragraph("Расписание собеседований", title_style))

            # 1. Формируем данные
            data = [['№', 'ФИО Волонтера', 'Телефон', 'Время']]
            start_time = datetime.strptime("09:00", "%H:%M")
            group_size = 30

            for i, v in enumerate(volunteers_list):
                group_num = i // group_size
                if i % group_size == 0:
                    t_start = start_time + timedelta(minutes=group_num * 30)
                    t_end = t_start + timedelta(minutes=30)
                    time_text = f"{t_start.strftime('%H:%M')} - {t_end.strftime('%H:%M')}"
                else:
                    time_text = ""

                data.append([
                    str(i + 1), 
                    str(v.full_name or "---")[:40], # Ограничим длину имени
                    str(v.phone_number or "---"), 
                    time_text
                ])

            # 2. Стили (Базовые)
            style_config = [
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                
                # Цвета столбцов (Пастель)
                ('BACKGROUND', (0, 1), (0, -1), colors.HexColor("#FEF9E7")),
                ('BACKGROUND', (1, 1), (1, -1), colors.HexColor("#E9F7EF")),
                ('BACKGROUND', (2, 1), (2, -1), colors.HexColor("#EBF5FB")),
                ('BACKGROUND', (3, 1), (3, -1), colors.HexColor("#F8F9F9")),

                # Шапка
                ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#FAD7A0")),
                ('BACKGROUND', (1, 0), (1, 0), colors.HexColor("#A9DFBF")),
                ('BACKGROUND', (2, 0), (2, 0), colors.HexColor("#AED6F1")),
                ('BACKGROUND', (3, 0), (3, 0), colors.HexColor("#D5DBDB")),

                # Границы
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black), # Сначала общая тонкая сетка
                ('BOX', (0, 0), (-1, -1), 1.2, colors.black),
                ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black), # Жирная под шапкой
            ]

            # 3. SPAN и Жирные линии (Расчет индексов)
            for start_row in range(1, len(data), group_size):
                end_row = start_row + group_size - 1
                if end_row >= len(data):
                    end_row = len(data) - 1
                
                # Объединяем время
                style_config.append(('SPAN', (3, start_row), (3, end_row)))
                
                # Жирная линия между группами
                if end_row < len(data) - 1:
                    style_config.append(('LINEBELOW', (0, end_row), (-1, end_row), 2, colors.black))

            # КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: Задаем высоту каждой строки вручную (например, 25 единиц)
            # Это предотвращает расчет rh (row heights) внутри ReportLab, который выдавал ошибку.
            row_heights = [30] + [22] * (len(data) - 1)

            table = Table(data, colWidths=[35, 215, 125, 115], rowHeights=row_heights)
            table.setStyle(TableStyle(style_config))
            elements.append(table)
            
            doc.build(elements)
            buffer.seek(0)
            
            return FileResponse(buffer, as_attachment=True, filename="Schedule.pdf")

        except Exception as e:
            import traceback
            print(f"!!! КРИТИЧЕСКАЯ ОШИБКА PDF: {str(e)}")
            traceback.print_exc()
            return Response({"error": f"Ошибка генерации: {str(e)}"}, status=500)
# ---------------- Страница Доски ----------------

class DownloadAcceptedNamesView(APIView):
    permission_classes = []

    def get(self, request):
        try:
            volunteers = VolunteerApplication.objects.filter(
                status='accepted'
            ).order_by('full_name')

            if not volunteers.exists():
                return Response(
                    {"error": "Список принятых волонтеров пуст"},
                    status=400
                )

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=40, leftMargin=40,
                topMargin=40, bottomMargin=40
            )

            elements = []

            # --- Шрифт ---
            font_name = 'Helvetica'
            font_path = os.path.join(settings.BASE_DIR, 'FreeSans.ttf')
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('FreeSans', font_path))
                    font_name = 'FreeSans'
                except:
                    pass

            title_style = ParagraphStyle(
                'Title',
                fontName=font_name,
                fontSize=18,
                alignment=1,
                spaceAfter=20
            )

            elements.append(Paragraph("Список принятых волонтеров", title_style))

            # --- Таблица: Только ФИО ---
            data = [['ФИО']]  # Только заголовок ФИО

            for v in volunteers:
                data.append([v.full_name or '---'])

            # Растягиваем колонку ФИО на всю ширину (примерно 450-500 для A4)
            table = Table(
                data,
                colWidths=[450],
                rowHeights=[30] + [22] * (len(data) - 1)
            )

            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('FONTSIZE', (0, 1), (-1, -1), 10),

                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Выравнивание текста влево
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 15), # Отступ текста от края

                # Шапка
                ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#D6EAF8")),

                # Тело
                ('BACKGROUND', (0, 1), (0, -1), colors.HexColor("#FDFEFE")),

                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('BOX', (0, 0), (-1, -1), 1.2, colors.black),
                ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
            ]))

            elements.append(table)
            doc.build(elements)

            buffer.seek(0)
            return FileResponse(
                buffer,
                as_attachment=True,
                filename="Accepted_Volunteers_Names.pdf"
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Ошибка генерации PDF: {str(e)}"},
                status=500
            )

import random
import math

class DownloadDistributionByDirectionView(APIView):
    permission_classes = []

    def get(self, request):
        try:
            # 1. Загружаем данные
            all_volunteers = list(VolunteerApplication.objects.filter(status='accepted').prefetch_related('directions'))
            all_directions = list(set([d for app in all_volunteers for d in app.directions.all()]))
            
            if not all_volunteers or not all_directions:
                return Response({"error": "Нет данных для распределения"}, status=400)

            # Перемешиваем волонтеров для честного рандома
            random.shuffle(all_volunteers)

            # Лимит человек на одно направление (с запасом вверх)
            limit = math.ceil(len(all_volunteers) / len(all_directions))
            
            # Итоговая структура: { Направление: [Список имен] }
            distribution = {d.name: [] for d in all_directions}
            
            # Список тех, кто не влез в свои приоритеты
            leftovers = []

            # 2. АЛГОРИТМ РОМНОГО РАСПРЕДЕЛЕНИЯ
            for app in all_volunteers:
                # Очистка имени
                parts = (app.full_name or "").strip().split()
                clean_name = " ".join(parts[:2]) if len(parts) >= 2 else (parts[0] if parts else "---")
                
                assigned = False
                # Пробуем приоритеты волонтера
                for direction in app.directions.all():
                    if len(distribution[direction.name]) < limit:
                        distribution[direction.name].append(clean_name)
                        assigned = True
                        break
                
                if not assigned:
                    leftovers.append(clean_name)

            # Рассовываем оставшихся туда, где меньше всего людей
            for person in leftovers:
                # Сортируем направления по текущему заполнению и берем самое пустое
                target_dir = min(distribution, key=lambda k: len(distribution[k]))
                distribution[target_dir].append(person)

            # 3. ГЕНЕРАЦИЯ КРАСИВОГО PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
            
            font_name = 'Helvetica'
            font_path = os.path.join(settings.BASE_DIR, 'FreeSans.ttf')
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('FreeSans', font_path))
                font_name = 'FreeSans'

            elements = []
            styles = getSampleStyleSheet()
            
            # Стили
            title_style = ParagraphStyle('Title', fontName=font_name, fontSize=20, alignment=1, spaceAfter=30, textColor=colors.HexColor("#283593"))
            header_style = ParagraphStyle('Header', fontName=font_name, fontSize=14, textColor=colors.white, leftIndent=10)
            count_style = ParagraphStyle('Count', fontName=font_name, fontSize=9, textColor=colors.grey, alignment=2)

            elements.append(Paragraph("ИТОГОВОЕ РАСПРЕДЕЛЕНИЕ КОМАНД", title_style))

            palette = ["#3949AB", "#00897B", "#8E24AA", "#D81B60", "#F4511E", "#039BE5"]

            for i, (dir_name, names) in enumerate(sorted(distribution.items())):
                color = palette[i % len(palette)]
                
                # Шапка направления
                header_data = [[Paragraph(dir_name.upper(), header_style), Paragraph(f"Итого: {len(names)} чел.", count_style)]]
                header_table = Table(header_data, colWidths=[380, 135])
                header_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(color)),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ]))
                elements.append(header_table)

                # Таблица с именами (в 2 колонки)
                random.shuffle(names) # Еще раз мешаем внутри для красоты
                table_data = []
                for j in range(0, len(names), 2):
                    row = [names[j]]
                    row.append(names[j+1] if j+1 < len(names) else "")
                    table_data.append(row)

                t = Table(table_data, colWidths=[257.5, 257.5])
                t.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), font_name),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F5F5F5")),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
                    ('LEFTPADDING', (0, 0), (-1, -1), 15),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ]))
                elements.append(t)
                elements.append(Spacer(1, 20))

            doc.build(elements)
            buffer.seek(0)
            return FileResponse(buffer, as_attachment=True, filename="Balanced_Distribution.pdf")

        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)
    permission_classes = []

    def get(self, request):
        try:
            # 1. Загружаем данные
            applications = VolunteerApplication.objects.filter(
                status='accepted'
            ).prefetch_related('directions')

            if not applications.exists():
                return Response({"error": "Нет данных для генерации"}, status=400)

            # 2. Распределяем по желаниям
            distribution = {}
            for app in applications:
                # Очистка ФИО: только Фамилия Имя
                parts = (app.full_name or "").strip().split()
                clean_name = " ".join(parts[:2]) if len(parts) >= 2 else (parts[0] if parts else "---")

                for direction in app.directions.all():
                    dir_name = direction.name
                    if dir_name not in distribution:
                        distribution[dir_name] = []
                    distribution[dir_name].append(clean_name)

            # --- РАНДОМИЗАЦИЯ ---
            for dir_name in distribution:
                random.shuffle(distribution[dir_name])

            # 3. Настройка PDF
            buffer = io.BytesIO()
            # Увеличим поля для эффекта "презентации"
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
            )

            # Регистрация шрифта (FreeSans поддерживает кириллицу)
            font_name = 'Helvetica'
            font_path = os.path.join(settings.BASE_DIR, 'FreeSans.ttf')
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('FreeSans', font_path))
                font_name = 'FreeSans'

            elements = []
            
            # --- СТИЛИ ---
            title_style = ParagraphStyle(
                'MainTitle',
                fontName=font_name,
                fontSize=22,
                alignment=1,
                spaceAfter=30,
                textColor=colors.HexColor("#1A237E") # Темно-синий
            )

            header_style = ParagraphStyle(
                'DirHeader',
                fontName=font_name,
                fontSize=14,
                leading=18,
                leftIndent=10,
                textColor=colors.whitesmoke,
                alignment=0
            )

            # 4. Построение контента
            elements.append(Paragraph("КОМАНДЫ ВОЛОНТЕРОВ", title_style))
            elements.append(Spacer(1, 10))

            # Цветовая схема для направлений (будет чередоваться)
            palette = ["#3F51B5", "#009688", "#673AB7", "#E91E63", "#FF9800", "#03A9F4"]

            for i, (dir_name, names) in enumerate(sorted(distribution.items())):
                color = palette[i % len(palette)]
                
                # Делаем "плашку" заголовка направления через таблицу
                header_table = Table([[Paragraph(dir_name.upper(), header_style)]], colWidths=[515])
                header_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(color)),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ]))
                elements.append(header_table)

                # Список волонтеров
                # Разбиваем список на 2 колонки для красоты, если людей много
                table_data = []
                for j in range(0, len(names), 2):
                    row = [names[j]]
                    if j + 1 < len(names):
                        row.append(names[j+1])
                    else:
                        row.append("")
                    table_data.append(row)

                content_table = Table(table_data, colWidths=[257.5, 257.5])
                content_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), font_name),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#424242")),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.white), # Белая сетка на сером фоне
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 15),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                
                elements.append(content_table)
                elements.append(Spacer(1, 25)) # Отступ между блоками

            doc.build(elements)
            buffer.seek(0)
            
            return FileResponse(
                buffer, 
                as_attachment=True, 
                filename=f"Volunteers_Teams_{datetime.now().strftime('%d_%m')}.pdf"
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)

class VolunteerBoardView(TemplateView):
    template_name = "volunteers/columns.html"