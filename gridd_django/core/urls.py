from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import views
from .api import ZoneViewSet, SensorViewSet, ObservationViewSet, AlertViewSet, health, latest_by_zone

router = DefaultRouter()
router.register("zones", ZoneViewSet, basename="zone")
router.register("sensors", SensorViewSet, basename="sensor")
router.register("observations", ObservationViewSet, basename="observation")
router.register("alerts", AlertViewSet, basename="alert")

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("legacy/", views.legacy_dashboard, name="legacy-dashboard"),
    path("zones/<slug:code>/", views.zone_dashboard, name="zone-dashboard"),
    path("api/health/", health, name="health"),
    path("api/zones/<slug:zone_code>/latest/", latest_by_zone, name="latest-by-zone"),
    path("api/", include(router.urls)),
]
