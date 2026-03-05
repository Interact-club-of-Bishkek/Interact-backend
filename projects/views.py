from django.utils import timezone
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, CreateAPIView, RetrieveAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny # Важный импорт
from rest_framework.views import APIView
from rest_framework import generics
from .models import FAQ, HeroSlide, Partner, Project, TeamMember, YearResult
from .serializers import FAQSerializer, HeroSlideSerializer, PartnerSerializer, ProjectSerializer, TeamMemberSerializer, YearResultSerializer

# --- Вспомогательная функция для архивации ---
def archive_expired_projects():
    now = timezone.now()
    Project.objects.filter(time_end__lt=now, is_archived=False).update(is_archived=True)

# 1. API для вывода 7 ближайших проектов (Главная страница)
class RecentProjectListView(ListAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        archive_expired_projects()
        queryset = Project.objects.select_related("direction").filter(
            is_archived=False
        ).order_by("time_start")[:7]
        return queryset


# --- HTML VIEWS ДЛЯ ПРОЕКТОВ (SSR) ---

# 2. Страница деталей одного проекта
def project_details_page(request, slug):
    try:
        # Ищем проект по слагу
        project = Project.objects.get(slug=slug)
    except Project.DoesNotExist:
        project = None
        
    return render(request, 'main_page/project-details.html', {'project': project})


# 3. Страница всех проектов (Каталог)
def projects_list_page(request):
    # 1. Автоматически архивируем прошедшие проекты перед выводом
    archive_expired_projects()

    # 2. Достаем все актуальные проекты
    projects = Project.objects.select_related("direction").filter(
        is_archived=False
    ).order_by("direction__name", "time_start")

    # 3. Группируем проекты по направлениям
    grouped_projects = {}
    for p in projects:
        dir_name = p.direction.name if p.direction else "Разное"
        
        if dir_name not in grouped_projects:
            grouped_projects[dir_name] = []
            
        grouped_projects[dir_name].append(p)

    return render(request, 'main_page/projects.html', {'grouped_projects': grouped_projects})


# --- ОСТАЛЬНЫЕ API ENDPOINTS ---

# 4. Архив (API)
class ProjectArchiveListView(ListAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Project.objects.select_related("direction").filter(
            is_archived=True
        ).order_by("-time_end")

        direction_id = self.request.query_params.get("direction_id")
        if direction_id:
            queryset = queryset.filter(direction_id=direction_id)

        return queryset

# 5. Создание (API)
class ProjectCreateAPIView(CreateAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny] 

class YearResultListView(APIView): 
    permission_classes = [AllowAny]

    def get(self, request):
        result = YearResult.objects.order_by('year').last()
        if result:
            serializer = YearResultSerializer(result)
            return Response(serializer.data)
        return Response({}, status=404)
    
class HeroSlideListView(ListAPIView):
    serializer_class = HeroSlideSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        return HeroSlide.objects.filter(is_active=True).order_by('order')
    
class TeamMemberListView(ListAPIView):
    queryset = TeamMember.objects.filter(is_active=True)
    serializer_class = TeamMemberSerializer
    permission_classes = [AllowAny]

class FAQListView(ListAPIView):
    queryset = FAQ.objects.all().order_by('order')
    serializer_class = FAQSerializer
    permission_classes = [AllowAny]
    
class PartnerListView(generics.ListAPIView):
    queryset = Partner.objects.filter(is_active=True)
    serializer_class = PartnerSerializer
    permission_classes = [AllowAny]


# --- ОСТАЛЬНЫЕ HTML VIEWS ---

def main_page(request):
    return render(request, 'main_page/main.html')

def promotion_page(request):
    return render(request, 'promotion/promotion.html')

def custom_page_not_found(request, exception):
    return render(request, 'error/404.html', status=404)

def about_page(request):
    return render(request, 'main_page/about.html')

def donate_page(request):
    return render(request, 'main_page/donate.html')

def sponsorship_page(request):
    return render(request, 'main_page/sponsorship.html')

def privacy_page(request):
    return render(request, 'main_page/privacy.html')

def terms_page(request):
    return render(request, 'main_page/terms.html')

def volunteer_page(request):
    return render(request, 'main_page/volunteer.html')  