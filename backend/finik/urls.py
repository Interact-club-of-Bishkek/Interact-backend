# urls.py
from django.urls import path
from .views import PaymentListCreateAPIView, CreatePaymentAPIView, FinikWebhookAPIView, PaymentStatusAPIView

urlpatterns = [
    path("api/payments/", PaymentListCreateAPIView.as_view(), name="payments-list-create"),
    path("api/pay/", CreatePaymentAPIView.as_view(), name="create-payment"),
    path("payments/callback/", FinikWebhookAPIView.as_view(), name="payments-callback"),
    path("api/payment-status/<str:payment_id>/", PaymentStatusAPIView.as_view(), name="payment-status")

]
