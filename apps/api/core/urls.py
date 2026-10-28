from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import auth_api
from .alarm_api import AlarmRuleViewSet
from .api import (
    AlertViewSet,
    ObservationViewSet,
    SensorViewSet,
    ZoneViewSet,
    health,
    latest_by_zone,
    zone_history,
)

# L'interface est une application séparée (web/) : le backend n'expose plus
# que l'API REST, l'admin Django et les WebSocket.
router = DefaultRouter()
router.register("zones", ZoneViewSet, basename="zone")
router.register("sensors", SensorViewSet, basename="sensor")
router.register("observations", ObservationViewSet, basename="observation")
router.register("alerts", AlertViewSet, basename="alert")
router.register("alarm-rules", AlarmRuleViewSet, basename="alarm-rule")

urlpatterns = [
    path("api/health/", health, name="health"),
    path("api/auth/token/", auth_api.obtain_token, name="auth-token"),
    path("api/auth/me/", auth_api.me, name="auth-me"),
    path("api/auth/logout/", auth_api.logout, name="auth-logout"),
    path("api/zones/<slug:zone_code>/latest/", latest_by_zone, name="latest-by-zone"),
    path("api/zones/<slug:zone_code>/history/", zone_history, name="zone-history"),
    path("api/", include(router.urls)),
]
