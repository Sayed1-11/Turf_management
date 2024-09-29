from rest_framework import viewsets
from .models import Turf
from .serializers import TurfSerializer
from rest_framework.response import Response
from datetime import timedelta,datetime

class TurfViewSet(viewsets.ModelViewSet):
    queryset = Turf.objects.all()
    serializer_class = TurfSerializer
