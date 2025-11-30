from django.shortcuts import render
from .models import Project, YearResult
from rest_framework.generics import ListAPIView
from .serializers import ProjectSerializer, YearResultSerializer
# Create your views here.

class ProjectListView(ListAPIView):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        queryset = (
            Project.objects
            .select_related("direction")
            .order_by("direction__name", "time_start")
        )

        direction_id = self.request.query_params.get("direction_id")
        if direction_id:
            queryset = queryset.filter(direction_id=direction_id)

        return queryset

class YearResultListView(ListAPIView):
    queryset = YearResult.objects.all()
    serializer_class = YearResultSerializer



