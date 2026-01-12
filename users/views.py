from rest_framework import viewsets, generics, status, serializers # Добавлен serializers
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from django.views.generic import TemplateView
from django.core.mail import send_mail
from django.conf import settings
import random
import string
from rest_framework.permissions import AllowAny # Импортируйте это

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
    permission_classes = []  # логин ВСЕГДА без токена

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
        user_id = self.request.user.id
        return Volunteer.objects.get(id=user_id)


# ---------------- Columns для фронта ----------------

# !!! ИСПРАВЛЕНИЕ ЗДЕСЬ !!!
class VolunteerColumnsSerializer(serializers.Serializer):
    # Используем VolunteerApplicationSerializer для ВСЕХ колонок,
    # чтобы ответы на вопросы (why_volunteer и т.д.) были доступны везде.
    submitted = VolunteerApplicationSerializer(many=True, read_only=True)
    interview = VolunteerApplicationSerializer(many=True, read_only=True)
    # Было VolunteerSerializer, стало VolunteerApplicationSerializer
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
                # Убираем явную передачу None, чтобы сработал метод save() модели
                volunteer = Volunteer.objects.create(
                    name=obj.full_name,
                    phone_number=obj.phone_number,
                    email=obj.email,
                    image=obj.photo # Копируем фото из анкеты
                )
                
                if obj.directions.exists():
                    volunteer.direction.set(obj.directions.all())
                
                # Привязываем созданного пользователя к анкете
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


# ---------------- Columns View (Исправлено) ----------------

class VolunteerColumnsView(APIView):
    """
    GET: возвращает три группы волонтёров для фронта
    """
    permission_classes = [] 

    def get(self, request):
        submitted = VolunteerApplication.objects.filter(status='submitted').order_by('-created_at')
        interview = VolunteerApplication.objects.filter(status='interview').order_by('-created_at')
        
        # !!! ИСПРАВЛЕНИЕ ЗДЕСЬ !!!
        # Мы запрашиваем VolunteerApplication, а не Volunteer.
        # Это гарантирует, что все поля анкеты будут переданы на фронт.
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
                print(f"[INFO] Отправка письма на {volunteer.email}")
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
                print(f"[SUCCESS] Письмо отправлено: {volunteer.email}")
                sent.append(volunteer.email)
            except Exception as e:
                print(f"[ERROR] Не удалось отправить письмо {volunteer.email}: {e}")
                failed.append({'email': volunteer.email, 'error': str(e)})
                continue

        return Response({
            'sent_to': sent,
            'failed': failed,
            'count_sent': len(sent),
            'count_failed': len(failed)
        })


class BotCheckAccessView(APIView):
    """
    Эндпоинт для проверки паролей из Telegram бота
    """
    permission_classes = [] # Доступ без токена, проверка идет по паролю

    def post(self, request):
        serializer = BotAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        access_type = serializer.validated_data['access_type']
        password = serializer.validated_data['password']

        # Получаем пароли из БД
        configs = {config.role: config.password for config in BotAccessConfig.objects.all()}
        
        curator_pass = configs.get('curator')
        volunteer_pass = configs.get('volunteer')

        # 1. Куратор всегда проходит
        if password == curator_pass:
            return Response({"status": "access_granted", "role": "curator"}, status=status.HTTP_200_OK)

        # 2. Волонтер проходит только в раздел команд
        if access_type == "commands" and password == volunteer_pass:
            return Response({"status": "access_granted", "role": "volunteer"}, status=status.HTTP_200_OK)

        return Response({"status": "access_denied"}, status=status.HTTP_403_FORBIDDEN)

class VolunteerBoardView(TemplateView):
    template_name = "volunteers/columns.html"


