from rest_framework import serializers
from .models import Booking

class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['full_name', 'phone', 'row', 'seat', 'price', 'hall_type']
