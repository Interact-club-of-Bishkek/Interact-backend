from django.shortcuts import render
from django.contrib.admin.models import LogEntry
import json

def logs_view(request):
    entries = LogEntry.objects.order_by("-action_time")  # не select_related

    logs = []

    for entry in entries:
        changes = {}
        try:
            msg = json.loads(entry.change_message)
            if isinstance(msg, list) and msg:
                item = msg[0]
                if "changed_real" in item:
                    changes = item["changed_real"]
        except:
            pass

        logs.append({
            "id": entry.id,
            "user": entry.user if entry.user else "Неизвестно",
            "action_flag": entry.action_flag,
            "model_name": entry.content_type.model_class()._meta.verbose_name.title()
                          if entry.content_type else "—",
            "object_id": entry.object_id,
            "object_repr": entry.object_repr,
            "action_time": entry.action_time,
            "changes": changes,
            "change_message": entry.change_message,  # для URL и времени
        })

    return render(request, "logs/logs.html", {"logs": logs})
