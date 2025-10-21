from .models import PaymentLog

def log_payment(level, message, extra=None):
    PaymentLog.objects.create(
        level=level,
        message=message,
        extra=extra or {}
    )
