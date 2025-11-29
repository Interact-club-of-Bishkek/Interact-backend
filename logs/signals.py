# signals.py
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils.timezone import now
from django.contrib.admin.models import LogEntry, ADDITION

@receiver(user_logged_in)
def log_admin_login(sender, request, user, **kwargs):
    if user.is_staff:
        LogEntry.objects.log_action(
            user_id=user.pk,
            content_type_id=None,
            object_id=None,
            object_repr="Admin login",
            action_flag=ADDITION,
            change_message=f"Admin {user.username} logged in at {now()}"
        )

@receiver(user_logged_out)
def log_admin_logout(sender, request, user, **kwargs):
    if user and user.is_staff:
        LogEntry.objects.log_action(
            user_id=user.pk,
            content_type_id=None,
            object_id=None,
            object_repr="Admin logout",
            action_flag=3,  # Можно использовать delete просто для обозначения выхода
            change_message=f"Admin {user.username} logged out at {now()}"
        )
