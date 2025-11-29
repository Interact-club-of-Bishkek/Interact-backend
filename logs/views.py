from django.shortcuts import render
from django.contrib.admin.models import LogEntry
import json

def logs_view(request):
    entries = LogEntry.objects.order_by("-action_time")

    logs = []

    for entry in entries:
        # обработка изменений
        changes = {}
        try:
            msg = json.loads(entry.change_message)
            if isinstance(msg, list) and msg:
                item = msg[0]
                if "changed_real" in item:
                    changes = item["changed_real"]
        except:
            pass

        # безопасное определение model_name
        model_cls = entry.content_type.model_class() if entry.content_type else None
        model_name = model_cls._meta.verbose_name.title() if model_cls else "—"

        logs.append({
            "id": entry.id,
            "user": entry.user if entry.user else "Неизвестно",
            "action_flag": entry.action_flag,
            "model_name": model_name,
            "object_id": entry.object_id,
            "object_repr": entry.object_repr,
            "action_time": entry.action_time,
            "changes": changes,
            "change_message": entry.change_message,
        })

    return render(request, "logs/logs.html", {"logs": logs})
