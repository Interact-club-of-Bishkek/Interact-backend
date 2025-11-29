import json
from django.db import models
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType


class LoggableModel(models.Model):
    """
    Базовый класс для логирования изменений.
    Используется в моделях через наследование.
    """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        is_new = self.pk is None
        old_state = None

        if request and hasattr(request, "_old_state"):
            old_state = request._old_state.get(type(self), {}).get(self.pk)

        super().save(*args, **kwargs)

        if request and old_state and not is_new:
            diff = {}
            for field in self._meta.fields:
                name = field.name
                old = old_state.get(name)
                new = getattr(self, name)
                if str(old) != str(new):
                    diff[name] = {"old": old, "new": new}

            if diff:
                from django.contrib.admin.models import LogEntry, CHANGE
                from django.contrib.contenttypes.models import ContentType
                import json

                LogEntry.objects.log_action(
                    user_id=request.user.pk,
                    content_type_id=ContentType.objects.get_for_model(self).pk,
                    object_id=self.pk,
                    object_repr=str(self),
                    action_flag=CHANGE,
                    change_message=json.dumps([{"changed_real": diff}])
                )
