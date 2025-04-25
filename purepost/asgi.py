import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

from purepost.message_service.auth_middleware import TokenAuthMiddleware

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "purepost.settings")
# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

from purepost.message_service.routing import websocket_urlpatterns as message_websocket_urlpatterns
from purepost.notification_service.routing import websocket_urlpatterns as notification_websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": TokenAuthMiddleware(URLRouter([
            *message_websocket_urlpatterns,
            *notification_websocket_urlpatterns,
        ])),
    }
)
