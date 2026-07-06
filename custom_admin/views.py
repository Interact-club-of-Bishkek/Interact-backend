import json
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q

from users.models import Volunteer, VolunteerApplication, AppSettings, ActivitySubmission
from projects.models import Project  # Убедись, что путь к модели Project правильный!


def is_admin_or_curator(user):
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.is_staff or getattr(user, 'role', '') in ['admin', 'curator']


class AdminDashboardView(UserPassesTestMixin, TemplateView):
    template_name = 'volunteers/admin_panel.html'
    login_url = '/admin/login/' 

    def test_func(self):
        return is_admin_or_curator(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # 1. Проекты
        context['projects'] = Project.objects.all().order_by('-time_start')
        
        # 2. Волонтеры (🔥 ОПТИМИЗАЦИЯ: Считаем желтые карточки в БД за 1 запрос!)
        # Сортировка по '-point' автоматически формирует рейтинг (в HTML используем forloop.counter)
        context['volunteers'] = Volunteer.objects.prefetch_related('direction').annotate(
            yc_count=Count('yellow_cards', distinct=True)
        ).order_by('-point')
        
        # 3. Новые заявки в волонтеры (статус 'submitted')
        context['pending_apps'] = VolunteerApplication.objects.filter(status='submitted').select_related('direction')
        
        # 4. 🔥 НОВОЕ: Отчеты по заданиям (учитываем ограничение видимости для кураторов из твоего admin.py)
        submissions_qs = ActivitySubmission.objects.filter(status='pending').select_related('volunteer', 'task', 'task__command')
        if not (user.is_superuser or getattr(user, 'role', '') == 'admin'):
            submissions_qs = submissions_qs.filter(
                Q(task__command__leader=user) | 
                Q(volunteer__direction__responsible=user)
            ).distinct()
        context['pending_submissions'] = submissions_qs
        
        # 5. Настройки системы (все 3 рубильника)
        context['app_settings'] = AppSettings.get_settings()
        
        return context


# --- AJAX API ЕНДПОИНТЫ ---

@require_POST
@user_passes_test(is_admin_or_curator)
def toggle_settings(request):
    data = json.loads(request.body)
    setting_type = data.get('type')
    value = data.get('value')
    
    settings = AppSettings.get_settings()
    if setting_type == 'registration': settings.is_registration_open = value
    elif setting_type == 'direction': settings.is_direction_selection_open = value
    elif setting_type == 'points': settings.is_points_submission_open = value
    settings.save()
    
    return JsonResponse({"status": "success"})


@require_POST
@user_passes_test(is_admin_or_curator)
def handle_application(request):
    data = json.loads(request.body)
    app_id = data.get('id')
    action = data.get('action')
    
    application = get_object_or_404(VolunteerApplication, id=app_id)
    if action == 'accept': application.status = 'accepted'
    elif action == 'reject': application.status = 'rejected'
    application.save()
    
    return JsonResponse({"status": "success", "new_status": application.status})


@require_POST
@user_passes_test(is_admin_or_curator)
def handle_submission(request):
    """🔥 НОВОЕ: Одобрение или отклонение отчета по заданию прямо со страницы"""
    data = json.loads(request.body)
    sub_id = data.get('id')
    action = data.get('action') # 'approve' или 'reject'
    
    submission = get_object_or_404(ActivitySubmission, id=sub_id)
    if action == 'approve':
        submission.status = 'approved'
    elif action == 'reject':
        submission.status = 'rejected'
    submission.save() # Это автоматически пересчитает баллы через твой метод в save()!
    
    return JsonResponse({"status": "success", "new_status": submission.status})


@require_POST
@user_passes_test(is_admin_or_curator)
def update_volunteer_points(request):
    data = json.loads(request.body)
    vol_id = data.get('id')
    points_to_add = int(data.get('points', 0))
    
    volunteer = get_object_or_404(Volunteer, id=vol_id)
    volunteer.point = (volunteer.point or 0) + points_to_add
    volunteer.save()
    
    return JsonResponse({"status": "success", "new_points": volunteer.point})