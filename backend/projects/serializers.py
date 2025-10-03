from rest_framework import serializers
from .models import Project, YearResult
from users.models import Direction


class DirectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Direction
        fields = ('name',) 
        ref_name = 'ProjectsDirectionSerializer' 
        
class YearResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = YearResult
        fields = '__all__'

class ProjectSerializer(serializers.ModelSerializer):
    direction = DirectionSerializer(read_only=True)

    class Meta:
        model = Project
        fields = ('image', 'name', 'title', 'price', 'date', 'direction')
