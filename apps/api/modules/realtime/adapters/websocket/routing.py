from django.urls import re_path

from .dashboard_websocket import DashboardWebSocket
from .zone_websocket import ZoneWebSocket

websocket_urlpatterns = [
    re_path(r"^ws/dashboard/$", DashboardWebSocket.as_asgi()),
    re_path(r"^ws/zones/(?P<zone_code>[-\w]+)/$", ZoneWebSocket.as_asgi()),
]
