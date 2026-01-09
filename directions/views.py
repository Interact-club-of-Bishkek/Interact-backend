# directions/views.py
from rest_framework import viewsets
from django.db.models import Prefetch

from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny
from .models import VolunteerDirection, ProjectDirection
from projects.models import Project
from .serializers import VolunteerDirectionSerializer, ProjectDirectionSerializer

class VolunteerDirectionViewSet(viewsets.ModelViewSet):
    queryset = VolunteerDirection.objects.prefetch_related('volunteers').all()
    serializer_class = VolunteerDirectionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class ProjectDirectionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProjectDirectionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # Автоархивирование перед выборкой
        Project.archive_expired()

        return ProjectDirection.objects.prefetch_related(
            Prefetch(
                'projects',
                queryset=Project.objects.filter(is_archived=False).order_by('time_start')
            )
        ).all()
    
