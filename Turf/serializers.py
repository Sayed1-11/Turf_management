from rest_framework import serializers
from .models import Turf,Facility,FieldSize
from datetime import datetime,time
from decimal import Decimal
from User.models import UserModel

class TurfSerializer(serializers.ModelSerializer):
    facilities = serializers.PrimaryKeyRelatedField(queryset=Facility.objects.all(), many=True)
    class Meta:
        model = Turf
        fields = ['name', 'location', 'image', 'facilities', 'rating','availble_offers','sports' ]
        read_only_fields = ['rating']

    def create(self, validated_data):
        facilities_data = validated_data.pop('facilities')
        
        turf = Turf.objects.create(**validated_data)
        turf.facilities.set(facilities_data)
        
        return turf