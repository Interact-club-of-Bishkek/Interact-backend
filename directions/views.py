# directions/views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import VolunteerDirection, ProjectDirection
from .serializers import VolunteerDirectionSerializer, ProjectDirectionSerializer

class VolunteerDirectionViewSet(viewsets.ModelViewSet):
    queryset = VolunteerDirection.objects.prefetch_related('volunteers').all()
    serializer_class = VolunteerDirectionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class ProjectDirectionViewSet(viewsets.ModelViewSet):
    queryset = ProjectDirection.objects.prefetch_related('projects').all()
    serializer_class = ProjectDirectionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
