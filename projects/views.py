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
    permission_classes = [AllowAny] # <-- ДОБАВЛЕНО: Разрешить всем

    def get_queryset(self):
        archive_expired_projects()
        queryset = Project.objects.select_related("direction").filter(
            is_archived=False
        ).order_by("time_start")[:7]
        return queryset

# 2. API для вывода одного проекта (Детальная страница)
class ProjectDetailView(RetrieveAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    lookup_field = 'id'
    permission_classes = [AllowAny] # <-- ДОБАВЛЕНО: Разрешить всем

# 3. API для вывода ВСЕХ проектов (Отдельная страница)
class ProjectListView(ListAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [AllowAny] # <-- ДОБАВЛЕНО: Разрешить всем

    def get_queryset(self):
        archive_expired_projects()
        queryset = Project.objects.select_related("direction").filter(
            is_archived=False
        ).order_by("direction__name", "time_start")

        direction_id = self.request.query_params.get("direction_id")
        if direction_id:
            queryset = queryset.filter(direction_id=direction_id)

        return queryset

# 4. Архив
class ProjectArchiveListView(ListAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [AllowAny] # <-- ДОБАВЛЕНО: Разрешить всем

    def get_queryset(self):
        queryset = Project.objects.select_related("direction").filter(
            is_archived=True
        ).order_by("-time_end")

        direction_id = self.request.query_params.get("direction_id")
        if direction_id:
            queryset = queryset.filter(direction_id=direction_id)

        return queryset

# 5. Создание (Оставляем AllowAny или меняем на IsAuthenticated, если нужно закрыть создание)
class ProjectCreateAPIView(CreateAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny] 

class YearResultListView(APIView): 
    permission_classes = [AllowAny]

    def get(self, request):
        # Гарантированно берем самую свежую запись именно по значению года
        result = YearResult.objects.order_by('year').last()
        
        if result:
            serializer = YearResultSerializer(result)
            return Response(serializer.data)
        return Response({}, status=404)
    
class HeroSlideListView(ListAPIView):
    serializer_class = HeroSlideSerializer
    permission_classes = [AllowAny]
    pagination_class = None  # Отключаем пагинацию для слайдера

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
    # HTML Views
def main_page(request):
    return render(request, 'main_page/main.html')

def test_page(request):
    return render(request, 'main_page/test.html')

def promotion_page(request):
    return render(request, 'promotion/promotion.html')

def custom_page_not_found(request, exception):
    return render(request, 'error/404.html', status=404)

def project_details_page(request):
    # Убедитесь, что файл project-details.html лежит в папке templates/projects/ 
    # или просто templates/ (зависит от вашей структуры).
    # Если файл лежит просто в templates, путь будет 'project-details.html'
    return render(request, 'main_page/project-details.html') 

def projects_list_page(request):
    # Для страницы "Все проекты" (projects.html)
    return render(request, 'main_page/projects.html')

# --- HTML Views для отображения страниц ---

def about_page(request):
    # Убедитесь, что путь к шаблону верный
    return render(request, 'main_page/about.html')

def donate_page(request):
    # Страница "В разработке", которую мы создали
    return render(request, 'main_page/donate.html')

def sponsorship_page(request):
    # Создайте файл templates/main_page/sponsorship.html
    return render(request, 'main_page/sponsorship.html')

def privacy_page(request):
    # Создайте файл templates/main_page/privacy.html
    return render(request, 'main_page/privacy.html')

def terms_page(request):
    # Создайте файл templates/main_page/terms.html
    return render(request, 'main_page/terms.html')

def volunteer_page(request):
    # Создайте файл templates/main_page/volunteer.html
    return render(request, 'main_page/volunteer.html')