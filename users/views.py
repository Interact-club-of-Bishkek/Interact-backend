import io
import os
import random
import string
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
            # Получаем волонтеров
            volunteers_list = list(VolunteerApplication.objects.filter(status='interview').order_by('full_name'))
            num_volunteers = len(volunteers_list)
            
            if num_volunteers == 0:
                return Response({"error": "Нет волонтеров со статусом interview"}, status=400)

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer, 
                pagesize=A4,
                rightMargin=35, leftMargin=35, topMargin=40, bottomMargin=40
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

            # Заголовок
            title_style = ParagraphStyle(
                'TitleStyle', fontName=font_name, fontSize=18,
                alignment=1, textColor=colors.HexColor("#333333"), spaceAfter=35
            )
            elements.append(Paragraph("Расписание собеседований", title_style))

            # Данные таблицы (Шапка - индекс 0)
            data = [['№', 'ФИО Волонтера', 'Телефон', 'Время']]
            
            style_config = [
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                
                # Цвета шапки
                ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#FAD7A0")),
                ('BACKGROUND', (1, 0), (1, 0), colors.HexColor("#A9DFBF")),
                ('BACKGROUND', (2, 0), (2, 0), colors.HexColor("#AED6F1")),
                ('BACKGROUND', (3, 0), (3, 0), colors.HexColor("#D5DBDB")),
                
                # Цвета столбцов (Пастель)
                ('BACKGROUND', (0, 1), (0, -1), colors.HexColor("#FEF9E7")),
                ('BACKGROUND', (1, 1), (1, -1), colors.HexColor("#E9F7EF")),
                ('BACKGROUND', (2, 1), (2, -1), colors.HexColor("#EBF5FB")),
                ('BACKGROUND', (3, 1), (3, -1), colors.HexColor("#F8F9F9")),

                # Черные границы столбцов
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('LINEBEFORE', (1, 0), (1, -1), 1, colors.black),
                ('LINEBEFORE', (2, 0), (2, -1), 1, colors.black),
                ('LINEBEFORE', (3, 0), (3, -1), 1, colors.black),
                ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
                
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
            ]

            start_time = datetime.strptime("09:00", "%H:%M")
            group_size = 30

            for i, v in enumerate(volunteers_list):
                # row_in_table — это индекс в списке `data`. 
                # Так как data[0] это шапка, то первый волонтер (i=0) будет в data[1].
                row_in_table = i + 1 
                
                # Каждые 30 человек делаем блок времени
                if i % group_size == 0:
                    group_idx = i // group_size
                    t_start = start_time + timedelta(minutes=group_idx * 30)
                    t_end = t_start + timedelta(minutes=30)
                    time_label = f"{t_start.strftime('%H:%M')} - {t_end.strftime('%H:%M')}"
                    
                    # Рассчитываем, до какой строки объединять (SPAN)
                    # Номер последней строки в группе: текущая + 29 (но не больше общего кол-ва)
                    last_row_in_group = min(row_in_table + group_size - 1, num_volunteers)
                    
                    # Объединяем ячейки времени
                    style_config.append(('SPAN', (3, row_in_table), (3, last_row_in_group)))
                    
                    # Если этот блок не последний, рисуем жирную черную линию снизу
                    if last_row_in_group < num_volunteers:
                        style_config.append(('LINEBELOW', (0, last_row_in_group), (-1, last_row_in_group), 2, colors.black))
                else:
                    time_label = ""

                data.append([
                    str(i + 1), 
                    str(v.full_name or "---"), 
                    str(v.phone_number or "---"), 
                    time_label
                ])

            table = Table(data, colWidths=[35, 210, 130, 115])
            table.setStyle(TableStyle(style_config))
            elements.append(table)
            
            doc.build(elements)
            buffer.seek(0)
            
            return FileResponse(buffer, as_attachment=True, filename="Interview_Schedule.pdf")

        except Exception as e:
            # Печатаем ошибку в лог докера, чтобы мы могли её увидеть
            print(f"!!! КРИТИЧЕСКАЯ ОШИБКА: {str(e)}")
            return Response({"error": f"Internal error: {str(e)}"}, status=500)
# ---------------- Страница Доски ----------------

class VolunteerBoardView(TemplateView):
    template_name = "volunteers/columns.html"