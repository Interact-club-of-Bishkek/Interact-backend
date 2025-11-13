# views.py
from rest_framework import viewsets, generics, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.conf import settings
import random
import string

from .models import Volunteer, VolunteerApplication
from .serializers import (
    VolunteerSerializer, VolunteerLoginSerializer,
    VolunteerApplicationSerializer, VolunteerApplicationStatusUpdateSerializer
)


# ---------------- Volunteers ----------------
class VolunteerViewSet(viewsets.ModelViewSet):
    queryset = Volunteer.objects.all()
    serializer_class = VolunteerSerializer


class VolunteerLoginView(APIView):
    def post(self, request):
        serializer = VolunteerLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        volunteer = serializer.validated_data["volunteer"]

        refresh = RefreshToken.for_user(volunteer)
        refresh["volunteer_id"] = volunteer.id
        access_token = refresh.access_token
        access_token["volunteer_id"] = volunteer.id

        return Response({
            "access": str(access_token),
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


# ---------------- Volunteer Applications ----------------
class VolunteerApplicationViewSet(viewsets.ModelViewSet):
    queryset = VolunteerApplication.objects.all().order_by('-created_at')
    serializer_class = VolunteerApplicationSerializer

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
                volunteer = Volunteer.objects.create_user(
                    login=None,
                    password=None,
                    name=obj.full_name,
                    phone_number=obj.phone_number,
                    email=obj.email
                )
                volunteer.direction.set(obj.directions.all())
                volunteer.save()
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

            # Используем visible_password
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


# ---------------- Columns для фронта ----------------
from rest_framework import serializers

class VolunteerColumnsSerializer(serializers.Serializer):
    submitted = VolunteerApplicationSerializer(many=True, read_only=True)
    interview = VolunteerApplicationSerializer(many=True, read_only=True)
    accepted = VolunteerSerializer(many=True, read_only=True)


class VolunteerColumnsView(APIView):
    """
    GET: возвращает три группы волонтёров для фронта
    """
    permission_classes = [IsAdminUser]  # только админ видит
    def get(self, request):
        submitted = VolunteerApplication.objects.filter(status='submitted').order_by('-created_at')
        interview = VolunteerApplication.objects.filter(status='interview').order_by('-created_at')
        accepted = VolunteerApplication.objects.filter(status='accepted', volunteer_created=True).select_related('volunteer').order_by('-created_at')

        serializer = VolunteerColumnsSerializer({
            'submitted': submitted,
            'interview': interview,
            'accepted': [v.volunteer for v in accepted if v.volunteer]
        })
        return Response(serializer.data)

class SendAcceptedVolunteersEmailsView(APIView):
    """
    Отправляет письма всем волонтёрам со статусом 'accepted' и с созданным аккаунтом.
    Права доступа сняты — любой может вызвать POST.
    """
    permission_classes = []  # снимаем проверку администратора

    def post(self, request):
        # Выбираем всех принятых волонтёров с аккаунтами
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

            # Используем видимый пароль или генерируем новый
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
