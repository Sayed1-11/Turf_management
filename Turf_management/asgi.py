import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from Turf.routing import websocket_urlpatterns  # Adjust the path if necessary

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Turf_management.settings')

# Get the ASGI application
application = get_asgi_application()

# Set up the ASGI application to handle WebSocket connections
application = ProtocolTypeRouter({
    "http": application,  # HTTP requests are handled by the default ASGI application
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                websocket_urlpatterns  # URL patterns for WebSocket connections
            )
        )
    ),
})
