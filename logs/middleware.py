from django.utils.deprecation import MiddlewareMixin
from django.contrib.admin.models import LogEntry, ADDITION
from django.urls import resolve
from django.contrib.admin.sites import site
from logs.loggable_model import LoggableModel


class AdminPageLoggingMiddleware(MiddlewareMixin):
    EXCLUDE_PATHS = [
        "/admin/jsi18n/", "/admin/login/", "/admin/logout/",
        "/admin/password_change/", "/admin/password_change/done/",
        "/admin/password_reset/", "/admin/password_reset/done/",
        "/admin/reset/", "/admin/reset/done/",
    ]

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not (request.user.is_staff and request.path.startswith("/admin/") and request.path not in self.EXCLUDE_PATHS):
            return None

        try:
            match = resolve(request.path)
            url_name = match.url_name
            page_name = None

            for model, model_admin in site._registry.items():
                opts = model._meta
                model_name_lower = opts.model_name.lower()

                if url_name == f"{model_name_lower}_changelist":
                    page_name = opts.verbose_name_plural  # Берём русское множественное имя
                    break
                elif url_name == f"{model_name_lower}_change":
                    obj_id = view_kwargs.get("object_id")
                    page_name = f"Изменение {opts.verbose_name}" + (f" (ID {obj_id})" if obj_id else "")
                    break
                elif url_name == f"{model_name_lower}_add":
                    page_name = f"Создание {opts.verbose_name}"
                    break

            if not page_name:
                page_name = request.path.strip("/").split("/")[-1].replace("_", " ")

            LogEntry.objects.log_action(
                user_id=request.user.pk,
                content_type_id=None,
                object_id=None,
                object_repr="Admin page view",
                action_flag=ADDITION,
                change_message=page_name
            )

        except Exception as e:
            print("AdminPageLoggingMiddleware error:", e)

        return None
    
class OldStateMiddleware(MiddlewareMixin):
    """
    Сохраняем старое состояние всех моделей-наследников LoggableModel
    перед изменением в админке, чтобы потом сравнивать.
    """

    def process_request(self, request):
        request._old_state = {}

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method == "POST" and request.path.startswith("/admin/"):
            for model in LoggableModel.__subclasses__():
                request._old_state[model] = {}
                for obj in model.objects.all():
                    state = {field.name: getattr(obj, field.name) for field in obj._meta.fields}
                    request._old_state[model][obj.pk] = state
        return None
