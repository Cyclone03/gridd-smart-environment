from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import views
from .api import (
    AlertViewSet,
    ObservationViewSet,
    SensorViewSet,
    ZoneViewSet,
    health,
    latest_by_zone,
    zone_history,
)
from .views import update_temperature_min

router = DefaultRouter()
router.register("zones", ZoneViewSet, basename="zone")
router.register("sensors", SensorViewSet, basename="sensor")
router.register("observations", ObservationViewSet, basename="observation")
router.register("alerts", AlertViewSet, basename="alert")

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("spaces/", views.dashboard, name="dashboard-spaces"),
    path("history/", views.dashboard, name="dashboard-history"),
    path("alerts/", views.dashboard, name="dashboard-alerts"),
    path("legacy/", views.legacy_dashboard, name="legacy-dashboard"),
    path("zones/<slug:code>/", views.zone_dashboard, name="zone-dashboard"),
    path("api/health/", health, name="health"),
    path("api/zones/<slug:zone_code>/latest/", latest_by_zone, name="latest-by-zone"),
    path("api/zones/<slug:zone_code>/history/", zone_history, name="zone-history"),
    path("api/", include(router.urls)),
    path("api/zones/<str:zone_code>/thresholds/", update_temperature_min, name="update_temperature_min",),
]
