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
from .models import Payment
from .serializers import PaymentSerializer
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
