# urls.py
from django.urls import path
from .views import PaymentListCreateAPIView, CreatePaymentAPIView, FinikWebhookAPIView, \
        PaymentStatusAPIView, CreateProjectPaymentAPIView, FinikProjectWebhookAPIView, ProjectPaymentInitAPIView, \
        ProjectPaymentConfirmAPIView

urlpatterns = [
    path("api/payments/", PaymentListCreateAPIView.as_view(), name="payments-list-create"),
    path("api/pay/", CreatePaymentAPIView.as_view(), name="create-payment"),
    path("payments/callback/", FinikWebhookAPIView.as_view(), name="payments-callback"),
    path("api/payment-status/<str:payment_id>/", PaymentStatusAPIView.as_view(), name="payment-status"),

    path("project/<int:project_id>/pay/", CreateProjectPaymentAPIView.as_view(), name="project-pay"),
    path("project-webhook/", FinikProjectWebhookAPIView.as_view(), name="project-webhook"),
    path("projects/<int:pk>/pay/", ProjectPaymentInitAPIView.as_view(), name="project-pay-init"),
    path("projects/payments/<uuid:payment_id>/confirm/", ProjectPaymentConfirmAPIView.as_view(), name="project-pay-confirm"),

]
