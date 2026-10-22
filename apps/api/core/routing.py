from django.urls import re_path

from .consumers import (
    DashboardConsumer,
    ZoneRealtimeConsumer,
)


websocket_urlpatterns = [
    re_path(
        r"^ws/dashboard/$",
        DashboardConsumer.as_asgi(),
    ),

    re_path(
        r"^ws/zones/(?P<zone_code>[-\w]+)/$",
        ZoneRealtimeConsumer.as_asgi(),
    ),
]