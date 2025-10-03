from rest_framework import serializers
from .models import Payment, ProjectPayment

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ["status", "created_at"]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class ProjectPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPayment
        fields = (
            "payment_id", "project", "first_name", "last_name",
            "phone", "comment", "amount", "status", "payment_url"
        )
        read_only_fields = ("payment_id", "status", "payment_url")