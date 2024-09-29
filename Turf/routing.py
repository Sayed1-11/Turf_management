from django.urls import path
from .consumers import TurfSlotConsumer  # Ensure the path to your consumer is correct

websocket_urlpatterns = [
    path('ws/turf-slot/', TurfSlotConsumer.as_asgi()),  # Adjust the URL pattern as needed
]
