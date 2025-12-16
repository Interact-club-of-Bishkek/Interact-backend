# directions/serializers.py
from rest_framework import serializers
from .models import VolunteerDirection, ProjectDirection
from users.models import Volunteer
from projects.models import Project

class VolunteerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Volunteer
        fields = [
            'id', 'login', 'name', 'phone_number', 'email', 'image',
            'telegram_username', 'telegram_id', 'board', 'direction',
            'point', 'yellow_card'
        ]


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            'id', 'image', 'name', 'title', 'price',
            'time_start', 'time_end', 'direction', 'phone_number', 'address'
        ]
    ref_name = 'DirectionsProjectSerializer'

class VolunteerDirectionSerializer(serializers.ModelSerializer):
    volunteers = VolunteerSerializer(many=True, read_only=True)

    class Meta:
        model = VolunteerDirection
        fields = ['id', 'name', 'volunteers']


class ProjectDirectionSerializer(serializers.ModelSerializer):
    projects = ProjectSerializer(many=True, read_only=True)

    class Meta:
        model = ProjectDirection
        fields = ['id', 'name', 'projects']
    
