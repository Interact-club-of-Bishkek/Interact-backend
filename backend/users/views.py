from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password


from .models import Direction, Volunteer
from .serializers import DirectionSerializer, VolunteerSerializer, VolunteerLoginSerializer


class DirectionViewSet(viewsets.ModelViewSet):
    queryset = Direction.objects.all()
    serializer_class = DirectionSerializer

class VolunteerViewSet(viewsets.ModelViewSet):
    queryset = Volunteer.objects.all()
    serializer_class = VolunteerSerializer


class VolunteerLoginView(APIView):
    def post(self, request):
        serializer = VolunteerLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        volunteer = serializer.validated_data["volunteer"]

        refresh = RefreshToken()
        refresh["volunteer_id"] = volunteer.id
        access_token = refresh.access_token
        access_token["volunteer_id"] = volunteer.id

        return Response({
            "access": str(access_token),
            "refresh": str(refresh),
            "volunteer": {
                "id": volunteer.id,
                "name": volunteer.name,
                "login": volunteer.login,
                "board": volunteer.board,  # <--- добавь это поле сюда
            }
        })

class VolunteerProfileView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = VolunteerSerializer

    def get_object(self):
        user_id = self.request.user.id  # django уже определяет пользователя по токену
        return Volunteer.objects.get(id=user_id)
