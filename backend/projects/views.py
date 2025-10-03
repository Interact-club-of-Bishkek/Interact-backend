from django.shortcuts import render
from .models import Project, YearResult
from rest_framework.generics import ListAPIView
from .serializers import ProjectSerializer, YearResultSerializer
# Create your views here.

class ProjectListView(ListAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer


class YearResultListView(ListAPIView):
    queryset = YearResult.objects.all()
    serializer_class = YearResultSerializer



