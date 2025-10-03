import uuid
import time
import json
import logging
import requests
from urllib.parse import urljoin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView
from authorizer import Signer
from .models import Payment, ProjectPayment
from projects.models import Project, YearResult
from .serializers import PaymentSerializer, ProjectPaymentSerializer
from projects.serializers import ProjectSerializer
from .utils import log_payment


# Обычный логгер для консоли/файла
logger = logging.getLogger("finik_webhook")
logger.setLevel(logging.INFO)


class FinikWebhookAPIView(APIView):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        raw_data = request.body
        signature = request.headers.get("signature")
        path = "/finik/webhook/"

        # Лог входящего webhook
        log_payment("INFO", "Получен webhook", {
            "path": path,
            "signature": signature,
            "body": raw_data.decode("utf-8")
        })

        request_data = {
            "http_method": "POST",
            "path": path,
            "headers": {k.lower(): v for k, v in request.headers.items()
                        if k.lower().startswith("x-api-") or k.lower() == "host"},
            "query_string_parameters": None,
            "body": raw_data.decode("utf-8")
        }

        if "host" not in request_data["headers"]:
            request_data["headers"]["host"] = settings.FINIK_HOST
        try:
            signer = Signer(**request_data)
            signer.verify(signature, settings.FINIK_PUBLIC_PEM)
            log_payment("INFO", "Подпись webhook валидна", {"signature": signature})
            
        except Exception as e:
            log_payment("WARNING", "Невалидная подпись webhook", {"error": str(e)})
            return JsonResponse({"error": "Invalid signature", "detail": str(e)}, status=403)

        try:
            json_data = json.loads(raw_data)
        except Exception as e:
            log_payment("ERROR", "Ошибка парсинга JSON webhook", {"error": str(e)})
            return JsonResponse({"error": "Invalid JSON", "detail": str(e)}, status=400)

        payment_id = json_data.get("transactionId")
        status = json_data.get("status")

        log_payment("INFO", "Webhook payload", {"payment_id": payment_id, "status": status})

        status_map = {"SUCCEEDED": "success", "FAILED": "failed"}
        payment_status = status_map.get(status.upper(), "pending")

        try:
            payment = Payment.objects.get(payment_id=payment_id)
            payment.status = payment_status
            payment.save()
            log_payment("INFO", "Статус платежа обновлен", {"payment_id": payment_id, "status": payment_status})
            return JsonResponse({"success": True})
        except Payment.DoesNotExist:
            log_payment("ERROR", "Платеж не найден", {"payment_id": payment_id})
            return JsonResponse({"error": "Payment not found"}, status=404)


class CreatePaymentAPIView(APIView):
    def post(self, request):
        amount = request.data.get("amount")
        first_name = request.data.get("first_name")
        last_name = request.data.get("last_name")
        phone = request.data.get("phone")
        comment = request.data.get("comment")

        transaction_id = str(uuid.uuid4())
        log_payment("INFO", "Создание платежа", {
            "transaction_id": transaction_id,
            "amount": amount,
            "user": f"{first_name} {last_name}"
        })

        payment = Payment.objects.create(
            payment_id=transaction_id,
            amount=amount,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            comment=comment,
            status="pending",
        )

        body = {
            "Amount": amount,
            "CardType": "FINIK_QR",
            "PaymentId": transaction_id,
            "RedirectUrl": settings.FINIK_REDIRECT_URL,
            "Data": {
                "accountId": settings.FINIK_ACCOUNT_ID,
                "merchantCategoryCode": "0742",
                "name_en": "Interact Club of Bishkek",
                "webhookUrl": settings.FINIK_WEBHOOK_URL
            }
        }

        timestamp = str(int(time.time() * 1000))
        request_data = {
            "http_method": "POST",
            "path": "/v1/payment",
            "headers": {
                "Host": settings.FINIK_HOST,
                "x-api-key": settings.FINIK_API_KEY,
                "x-api-timestamp": timestamp,
            },
            "query_string_parameters": None,
            "body": body,
        }

        signature = Signer(**request_data).sign(settings.FINIK_PRIVATE_PEM)
        url = urljoin(settings.FINIK_BASE_URL, request_data["path"])

        try:
            resp = requests.post(
                url,
                headers={
                    "content-type": "application/json",
                    "x-api-key": settings.FINIK_API_KEY,
                    "x-api-timestamp": timestamp,
                    "signature": signature,
                },
                data=json.dumps(body, separators=(",", ":")),
                allow_redirects=False
            )
            log_payment("INFO", "Запрос к Finik выполнен", {
                "transaction_id": transaction_id,
                "status_code": resp.status_code
            })
        except Exception as e:
            log_payment("ERROR", "Ошибка при запросе к Finik", {
                "transaction_id": transaction_id,
                "error": str(e)
            })
            payment.status = "failed"
            payment.save()
            return JsonResponse({"error": "Ошибка при запросе к Finik"}, status=500)

        if resp.status_code in [200, 302]:
            try:
                payment_url = resp.json().get("payment_url")
            except Exception:
                payment_url = resp.headers.get("Location")
            log_payment("INFO", "Платёж создан успешно", {
                "transaction_id": transaction_id,
                "payment_url": payment_url
            })
            return JsonResponse({"payment_url": payment_url, "payment_id": transaction_id})
        else:
            log_payment("ERROR", "Finik API вернул ошибку", {
                "transaction_id": transaction_id,
                "status_code": resp.status_code,
                "response": resp.text
            })
            payment.status = "failed"
            payment.save()
            return JsonResponse({"error": resp.text}, status=resp.status_code)


class PaymentListCreateAPIView(ListCreateAPIView):
    queryset = Payment.objects.all().order_by('-created_at')
    serializer_class = PaymentSerializer


class PaymentStatusAPIView(APIView):
    def get(self, request, payment_id):
        try:
            payment = Payment.objects.get(payment_id=payment_id)
            log_payment("INFO", "Запрос статуса платежа", {
                "payment_id": payment_id,
                "status": payment.status
            })
            return Response({
                "payment_id": payment.payment_id,
                "status": payment.status,
                "amount": str(payment.amount)
            })
        except Payment.DoesNotExist:
            log_payment("WARNING", "Попытка получить несуществующий платеж", {
                "payment_id": payment_id
            })
            return Response({"error": "Payment not found"}, status=404)


class CreateProjectPaymentAPIView(APIView):
    def post(self, request, project_id):
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return JsonResponse({"error": "Project not found"}, status=404)

        transaction_id = str(uuid.uuid4())
        amount = project.price

        log_payment("INFO", "Создание платежа для проекта", {
            "transaction_id": transaction_id,
            "project": project.name,
            "amount": amount,
        })

        payment = ProjectPayment.objects.create(
            payment_id=transaction_id,
            project=project,
            amount=amount,
            status="pending",
        )

        body = {
            "Amount": amount,
            "CardType": "FINIK_QR",
            "PaymentId": transaction_id,
            "RedirectUrl": settings.FINIK_REDIRECT_URL,
            "Data": {
                "accountId": settings.FINIK_ACCOUNT_ID,
                "merchantCategoryCode": "0742",
                "name_en": "Interact Club of Bishkek",
                "webhookUrl": settings.FINIK_WEBHOOK_URL,
            }
        }

        timestamp = str(int(time.time() * 1000))
        request_data = {
            "http_method": "POST",
            "path": "/v1/payment",
            "headers": {
                "Host": settings.FINIK_HOST,
                "x-api-key": settings.FINIK_API_KEY,
                "x-api-timestamp": timestamp,
            },
            "query_string_parameters": None,
            "body": body,
        }

        signature = Signer(**request_data).sign(settings.FINIK_PRIVATE_PEM)
        url = urljoin(settings.FINIK_BASE_URL, request_data["path"])

        try:
            resp = requests.post(
                url,
                headers={
                    "content-type": "application/json",
                    "x-api-key": settings.FINIK_API_KEY,
                    "x-api-timestamp": timestamp,
                    "signature": signature,
                },
                data=json.dumps(body, separators=(",", ":")),
                allow_redirects=False
            )
        except Exception as e:
            log_payment("ERROR", "Ошибка при запросе к Finik", {
                "transaction_id": transaction_id,
                "error": str(e)
            })
            payment.status = "failed"
            payment.save()
            return JsonResponse({"error": "Ошибка при запросе к Finik"}, status=500)

        if resp.status_code in [200, 302]:
            try:
                payment_url = resp.json().get("payment_url")
            except Exception:
                payment_url = resp.headers.get("Location")
            return JsonResponse({"payment_url": payment_url, "payment_id": transaction_id})
        else:
            payment.status = "failed"
            payment.save()
            return JsonResponse({"error": resp.text}, status=resp.status_code)
        

class FinikProjectWebhookAPIView(APIView):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        raw_data = request.body
        signature = request.headers.get("signature")
        path = "/finik/project-webhook/"

        # логируем входящий webhook
        log_payment("INFO", "Получен webhook для проекта", {
            "path": path,
            "signature": signature,
            "body": raw_data.decode("utf-8")
        })

        request_data = {
            "http_method": "POST",
            "path": path,
            "headers": {k.lower(): v for k, v in request.headers.items()
                        if k.lower().startswith("x-api-") or k.lower() == "host"},
            "query_string_parameters": None,
            "body": raw_data.decode("utf-8")
        }

        if "host" not in request_data["headers"]:
            request_data["headers"]["host"] = settings.FINIK_HOST
        try:
            signer = Signer(**request_data)
            signer.verify(signature, settings.FINIK_PUBLIC_PEM)
        except Exception as e:
            return JsonResponse({"error": "Invalid signature"}, status=403)

        try:
            json_data = json.loads(raw_data)
        except Exception:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        payment_id = json_data.get("transactionId")
        status = json_data.get("status")

        try:
            payment = ProjectPayment.objects.get(payment_id=payment_id)
        except ProjectPayment.DoesNotExist:
            return JsonResponse({"error": "Project payment not found"}, status=404)

        status_map = {"SUCCEEDED": "success", "FAILED": "failed"}
        payment_status = status_map.get(status.upper(), "pending")
        payment.status = payment_status
        payment.save()

        if payment_status == "success":
            project = payment.project
            yr, _ = YearResult.objects.get_or_create(id=1)

            if project.category == "sport":
                yr.sport += 1
            elif project.category == "cyber_sport":
                yr.cyber_sport += 1
            elif project.category == "education":
                yr.education += 1
            elif project.category == "fundraising":
                yr.fundraising += 1
            elif project.category == "cultural":
                yr.cultural += 1

            yr.total_amount += int(project.price)
            yr.save()

        return JsonResponse({"success": True})


class ProjectPaymentInitAPIView(APIView):
    """GET: возвращает данные о проекте и ссылку на оплату (форму)"""

    def get(self, request, pk):
        try:
            project = Project.objects.get(pk=pk)
        except Project.DoesNotExist:
            return Response({"error": "Project not found"}, status=404)

        # Создаём "черновик" платежа
        payment = ProjectPayment.objects.create(
            project=project,
            amount=project.price,
        )

        # Ссылка на форму для заполнения данных клиента
        # payment_link = f"{settings.FRONTEND_URL}/pay/{payment.payment_id}/"
        payment_link = f"/pay/{payment.payment_id}/"  # только для бэка

        return Response({
            "project": ProjectSerializer(project).data,
            "payment_id": str(payment.payment_id),
            "form_url": payment_link
        })
    

class ProjectPaymentConfirmAPIView(APIView):
    """POST: принимает данные клиента, создаёт платёж в Finik и возвращает ссылку"""

    def post(self, request, payment_id):
        try:
            payment = ProjectPayment.objects.get(payment_id=payment_id, status="pending")
        except ProjectPayment.DoesNotExist:
            return Response({"error": "Payment not found or already processed"}, status=404)

        payment.first_name = request.data.get("first_name")
        payment.last_name = request.data.get("last_name")
        payment.phone = request.data.get("phone")
        payment.comment = request.data.get("comment")
        payment.save()

        # --- Создание платежа в Finik ---
        body = {
            "Amount": str(payment.amount),
            "CardType": "FINIK_QR",
            "PaymentId": str(payment.payment_id),
            "RedirectUrl": settings.FINIK_REDIRECT_URL,
            "Data": {
                "accountId": settings.FINIK_ACCOUNT_ID,
                "merchantCategoryCode": "0742",
                "name_en": "Interact Club of Bishkek",
                "webhookUrl": settings.FINIK_WEBHOOK_URL
            }
        }

        timestamp = str(int(time.time() * 1000))
        request_data = {
            "http_method": "POST",
            "path": "/v1/payment",
            "headers": {
                "Host": settings.FINIK_HOST,
                "x-api-key": settings.FINIK_API_KEY,
                "x-api-timestamp": timestamp,
            },
            "query_string_parameters": None,
            "body": body,
        }

        signature = Signer(**request_data).sign(settings.FINIK_PRIVATE_PEM)
        url = urljoin(settings.FINIK_BASE_URL, request_data["path"])

        resp = requests.post(
            url,
            headers={
                "content-type": "application/json",
                "x-api-key": settings.FINIK_API_KEY,
                "x-api-timestamp": timestamp,
                "signature": signature,
            },
            data=json.dumps(body, separators=(",", ":")),
            allow_redirects=False
        )

        if resp.status_code in [200, 302]:
            try:
                payment_url = resp.json().get("payment_url")
            except Exception:
                payment_url = resp.headers.get("Location")

            payment.payment_url = payment_url
            payment.save()

            return Response({
                "payment_id": str(payment.payment_id),
                "payment_url": payment_url
            })
        else:
            payment.status = "failed"
            payment.save()
            return Response({"error": resp.text}, status=resp.status_code)