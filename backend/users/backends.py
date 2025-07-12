from django.contrib.auth.backends import BaseBackend
from .models import Volunteer

class VolunteerBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            volunteer = Volunteer.objects.get(login=username)
            if volunteer.check_password(password):
                return volunteer
        except Volunteer.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return Volunteer.objects.get(pk=user_id)
        except Volunteer.DoesNotExist:
            return None
