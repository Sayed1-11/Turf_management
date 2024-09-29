from rest_framework import viewsets,status
from .models import Coupon
from .serializers import CouponSerializer


class CuoponView(viewsets.ModelViewSet):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
