from django.utils import timezone
from rest_framework.generics import ListAPIView
from .models import Project, YearResult
from .serializers import ProjectSerializer, YearResultSerializer

class ProjectListView(ListAPIView):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        now = timezone.now()

        # Автоархивируем все проекты с прошедшей датой
        Project.objects.filter(time_end__lt=now, is_archived=False).update(is_archived=True)

        # queryset только для активных проектов
        queryset = Project.objects.select_related("direction").filter(is_archived=False).order_by("direction__name", "time_start")

        # Фильтрация по направлению, если передан параметр
        direction_id = self.request.query_params.get("direction_id")
        if direction_id:
            queryset = queryset.filter(direction_id=direction_id)

        return queryset


class ProjectArchiveListView(ListAPIView):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        queryset = Project.objects.select_related("direction").filter(is_archived=True).order_by("-time_end")

        # Фильтрация по направлению
        direction_id = self.request.query_params.get("direction_id")
        if direction_id:
            queryset = queryset.filter(direction_id=direction_id)

        return queryset


class YearResultListView(ListAPIView):
    queryset = YearResult.objects.all()
    serializer_class = YearResultSerializer
