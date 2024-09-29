from django.shortcuts import render
from rest_framework import viewsets,status
from rest_framework.decorators import action
from rest_framework.response import Response
from .utils import send_otp
from rest_framework.authtoken.models import Token
from django.utils.http import urlsafe_base64_encode,urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
import datetime
import random
from django.utils import timezone
from django.conf import settings
from .models import UserModel
from .serializers import UserSerializer,UserProfileUpdateSerializer
from rest_framework.permissions import IsAuthenticated
# Create your views here.
class UserViewset(viewsets.ModelViewSet):
    queryset = UserModel.objects.all()
    serializer_class = UserSerializer

    @action(detail=True, methods=['PATCH'])
    def verify_otp(self, request, pk=None):
        instance = self.get_object()
        if (not instance.is_active 
            and instance.otp==request.data.get('otp') 
            and instance.otp_expiry 
            and timezone.now()< instance.otp_expiry 
            ):
            instance.is_active = True
            instance.otp_expiry = None
            instance.max_otp_try = settings.MAX_OTP_TRY
            instance.otp_max_out = None
            instance.save()
            token = default_token_generator.make_token(instance)
            uid = urlsafe_base64_encode(force_bytes(instance))
            return Response({'message': 'OTP verified successfully.','token':token,'uid':uid}, status=status.HTTP_200_OK)
        return Response({'message': 'Please Enter the correct OTP'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['PATCH'])
    def generate_otp(self, request, pk=None):
        instance = self.get_object()
        if int(instance.max_otp_try) == 0 and timezone.now() < instance.otp_max_out:
            return Response(
                "Max OTP try reached, try after an hour",
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        otp = random.randint(1000, 9999)
        otp_expiry = timezone.now() + datetime.timedelta(minutes=10)
        max_otp_try = int(instance.max_otp_try)-1
        instance.otp = otp
        instance.otp_expiry = otp_expiry
        instance.max_otp_try = max_otp_try

        if max_otp_try == 0:
            otp_max_out = timezone.now() + datetime.timedelta(hours=1)
            instance.otp_max_out = otp_max_out
        elif max_otp_try == -1:
            instance.max_otp_try = settings.MAX_OTP_TRY
        else:
            instance.otp_max_out = None
            instance.max_otp_try = max_otp_try
        instance.save()
        send_otp(instance.phone_number,otp)
        return Response({'message': 'OTP generated successfully.', 'otp': otp}, status=status.HTTP_200_OK)
    


class UserProfileUpdateViewset(viewsets.ModelViewSet):
    queryset = UserModel.objects.all()
    serializer_class = UserProfileUpdateSerializer

    @action(detail=True, methods=['PATCH'])
    def update_profile(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Profile updated successfully.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

from rest_framework.authtoken.models import Token

def create_token_for_user(user):
    token, created = Token.objects.get_or_create(user=user)
    return token.key
