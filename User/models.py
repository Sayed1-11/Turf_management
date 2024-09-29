from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser,BaseUserManager,PermissionsMixin
from django.core.validators import RegexValidator,validate_email
# Create your models here.


phone_regex = RegexValidator(
    regex=r"^\d{11}",message="Phone number must be 11 digit only."
)

class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None):
        
        if phone_number is None:
            raise ValueError("Phone number must be provided.")
        user = self.model(phone_number=phone_number)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone_number, password):
        user = self.create_user(phone_number,password)
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class UserModel(AbstractBaseUser,PermissionsMixin):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
     
    phone_number = models.CharField(max_length=11,unique=True,null=False,blank=False,validators=[phone_regex])
    email = models.EmailField(null=True,blank=True, validators=[validate_email])
    name = models.CharField(max_length=255, null=True, blank=True)  
    birthdate = models.DateField(null=True, blank=True)  
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    address = models.TextField(null=True, blank=True)  
    otp = models.CharField(max_length=4)
    otp_expiry = models.DateTimeField(null=True, blank=True)
    max_otp_try = models.CharField(max_length=2,default=settings.MAX_OTP_TRY)
    otp_max_out = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    user_registered_at = models.DateTimeField(auto_now_add=True)
    USERNAME_FIELD = "phone_number"
    objects = UserManager()
    def __str__(self):
        return self.phone_number
    
    @property
    def username(self):
        return self.name if self.name else self.phone_number