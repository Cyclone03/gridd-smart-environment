import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.conf import settings  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402

django_asgi_application = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import OriginValidator  # noqa: E402

from core.routing import websocket_urlpatterns  # noqa: E402


# Le frontend est servi depuis un autre domaine que l'API : les WebSocket
# acceptent donc les hôtes de l'API et les origines CORS configurées
# (voir WEBSOCKET_ALLOWED_ORIGINS dans settings.py).
application = ProtocolTypeRouter(
    {
        "http": django_asgi_application,
        "websocket": OriginValidator(
            URLRouter(websocket_urlpatterns),
            settings.WEBSOCKET_ALLOWED_ORIGINS,
        ),
    }
)
