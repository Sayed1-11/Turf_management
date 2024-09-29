from django.contrib import admin
from .models import Facility,Turf,FieldSize,TurfSlot,TurfRating,SwimmingSlot,BadmintonSlot,SwimmingSession,Sports
# Register your models here.
admin.site.register(Facility)
admin.site.register(Turf)
admin.site.register(SwimmingSession)
admin.site.register(SwimmingSlot)
admin.site.register(FieldSize)
admin.site.register(TurfRating)
admin.site.register(BadmintonSlot)
admin.site.register(TurfSlot)
admin.site.register(Sports)