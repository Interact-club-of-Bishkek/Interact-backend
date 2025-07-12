from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
import asyncio
import nest_asyncio
import random
import string
from threading import Lock
from django.shortcuts import render
from bot import send_text_to_user
from form.models import TextMailing
from asgiref.sync import sync_to_async, async_to_sync
from datetime import datetime, timedelta
from form.models import VolunteerForm, WaitingList, VolunteerFormArchive, MailingPending
from users.models import Volunteer
from form.serializers import VolunteerFormSerializer, WaitingListSerializer, MailingPendingSerializer

from bot import send_account_data_to_users  # Импорт асинхронной функции из бота


class VerifyVolunteerFormView(APIView):
    def post(self, request, pk):
        try:
            form = VolunteerForm.objects.get(pk=pk)
        except VolunteerForm.DoesNotExist:
            return Response({"detail": "Заявка не найдена"}, status=status.HTTP_404_NOT_FOUND)

        if form.is_verified:
            return Response({"detail": "Заявка уже проверена"}, status=status.HTTP_400_BAD_REQUEST)

        form.is_verified = True
        form.save()

        waiting = WaitingList.objects.create(
            name=form.name,
            phone_number=form.phone_number,
            image=form.image,
            telegram_username=form.telegram_username,
            telegram_id=form.telegram_id
        )
        form.delete()

        # 📩 Отправка сообщения из TextMailing
        if waiting.telegram_id:
            try:
                text = TextMailing.objects.latest("id").text
            except TextMailing.DoesNotExist:
                text = "Ваша заявка прошла проверку и перенесена в лист ожидания ✅"

            # Асинхронная отправка
            nest_asyncio.apply()
            try:
                asyncio.run(send_text_to_user(waiting.telegram_id, text))
            except Exception as e:
                print(f"❌ Ошибка Telegram рассылки: {e}")

        return Response({"detail": f"Заявка перенесена в лист ожидания {waiting.name}"}, status=200)

class ApproveWaitingListView(APIView):
    def post(self, request, pk):
        try:
            waiting = WaitingList.objects.get(pk=pk)
        except WaitingList.DoesNotExist:
            return Response({"detail": "Не найден в листе ожидания"}, status=status.HTTP_404_NOT_FOUND)

        if waiting.is_approved:
            return Response({"detail": "Заявка уже прошла одобрение"}, status=status.HTTP_400_BAD_REQUEST)

        waiting.is_approved = True
        waiting.save()

        mailing = MailingPending.objects.create(
            name=waiting.name,
            phone_number=waiting.phone_number,
            image=waiting.image,
            telegram_username=waiting.telegram_username,
            telegram_id=waiting.telegram_id
        )
        waiting.delete()

        return Response({"detail": f"Заявка одобрена и перенесена в рассылку: {mailing.name}"}, status=200)


def generate_credentials(name):
    login = ''.join(e for e in name.lower() if e.isalnum())[:8] + str(random.randint(10, 99))
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    return login, password

approve_lock = Lock()

class ApproveAllFromMailingPendingView(APIView):
    def post(self, request):
        if not approve_lock.acquire(blocking=False):
            return Response({"detail": "Запрос уже выполняется"}, status=429)

        async def process_and_send():
            try:
                pendings = await sync_to_async(list)(MailingPending.objects.all())
                created = []

                for pending in pendings:
                    login, password = generate_credentials(pending.name)
                    volunteer = Volunteer(
                        name=pending.name,
                        phone_number=pending.phone_number,
                        image=pending.image,
                        telegram_username=pending.telegram_username,
                        telegram_id=pending.telegram_id,
                        login=login,
                        visible_password=password
                    )
                    await sync_to_async(volunteer.save)()
                    await sync_to_async(VolunteerFormArchive.objects.create)(
                        name=pending.name,
                        phone_number=pending.phone_number,
                        image=pending.image,
                        telegram_username=pending.telegram_username,
                        telegram_id=pending.telegram_id,
                        moved_to="volunteer"
                    )
                    if pending.telegram_id:
                        msg = (
                            f"👋 Привет, {pending.name}!\n\n"
                            f"Ты успешно добавлен в базу волонтёров!\n\n"
                            f"🔐 Логин: <code>{login}</code>\n"
                            f"🔑 Пароль: <code>{password}</code>"
                        )
                        await send_text_to_user(pending.telegram_id, msg)

                    created.append(pending.name)

                await sync_to_async(MailingPending.objects.all().delete)()
                return created

            finally:
                approve_lock.release()

        created_names = async_to_sync(process_and_send)()
        return Response({"detail": f"Создано и разослано: {created_names}"}, status=200)
    

class VolunteerFormListView(ListAPIView):
    queryset = VolunteerForm.objects.all()
    serializer_class = VolunteerFormSerializer


class WaitingListListView(ListAPIView):
    queryset = WaitingList.objects.all()
    serializer_class = WaitingListSerializer


class MailingPendingListView(ListAPIView):
    queryset = MailingPending.objects.all()
    serializer_class = MailingPendingSerializer


class MailingPendingDetailView(RetrieveAPIView):
    queryset = MailingPending.objects.all()
    serializer_class = MailingPendingSerializer


class VolunteerFormDetailView(RetrieveAPIView):
    queryset = VolunteerForm.objects.all()
    serializer_class = VolunteerFormSerializer


class WaitingListDetailView(RetrieveAPIView):
    queryset = WaitingList.objects.all()
    serializer_class = WaitingListSerializer

def schedule_view(request):
    # Сортируем волонтёров по имени по алфавиту
    volunteers = WaitingList.objects.all().order_by('name')

    start_time = datetime.strptime("09:00", "%H:%M")
    block_duration = timedelta(minutes=30)
    volunteers_per_block = 30

    rows = []

    for i in range(0, len(volunteers), volunteers_per_block):
        block_volunteers = volunteers[i:i+volunteers_per_block]
        interval_start = start_time + block_duration * (i // volunteers_per_block)
        interval_end = interval_start + block_duration
        interval_str = f"{interval_start.strftime('%H:%M')}-{interval_end.strftime('%H:%M')}"

        # Внутри блока отсортируем по имени, если нужно (обычно уже отсортированы)
        block_volunteers = sorted(block_volunteers, key=lambda v: v.name)

        for volunteer in block_volunteers:
            rows.append({
                "name": volunteer.name,
                "phone_number": volunteer.phone_number,
                "interval": interval_str,
            })

    return render(request, "schedule.html", {"rows": rows})