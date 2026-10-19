from django.db import connection
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import viewsets

from .models import Zone, Sensor, Observation, Alert
from .serializers import ZoneSerializer, SensorSerializer, ObservationSerializer, AlertSerializer


class ZoneViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Zone.objects.filter(active=True).order_by("name")
    serializer_class = ZoneSerializer


class SensorViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SensorSerializer

    def get_queryset(self):
        qs = Sensor.objects.select_related("zone").filter(active=True)
        zone = self.request.query_params.get("zone")
        if zone:
            qs = qs.filter(zone__code=zone)
        return qs.order_by("zone__name", "sensor_type")


class ObservationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ObservationSerializer

    def get_queryset(self):
        qs = Observation.objects.select_related("zone", "sensor")
        zone = self.request.query_params.get("zone")
        obs_type = self.request.query_params.get("type")
        if zone:
            qs = qs.filter(zone__code=zone)
        if obs_type:
            qs = qs.filter(type=obs_type)
        return qs[:1000]


class AlertViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AlertSerializer

    def get_queryset(self):
        qs = Alert.objects.select_related("zone", "observation")
        zone = self.request.query_params.get("zone")
        active = self.request.query_params.get("active")
        if zone:
            qs = qs.filter(zone__code=zone)
        if active in {"true", "false"}:
            qs = qs.filter(active=(active == "true"))
        return qs.order_by("-created_at")[:500]


@api_view(["GET"])
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        database = "connected"
        status = "ok"
    except Exception:
        database = "error"
        status = "degraded"

    return Response({
        "status": status,
        "database": database,
        "timestamp": timezone.now().isoformat(),
    })


@api_view(["GET"])
def latest_by_zone(request, zone_code):
    zone = Zone.objects.get(code=zone_code, active=True)
    result = {}
    for obs_type in ["temperature", "humidity", "co2", "sound_level", "occupancy"]:
        obs = (
            Observation.objects
            .filter(zone=zone, type=obs_type)
            .select_related("sensor")
            .order_by("-observed_at", "-received_at")
            .first()
        )
        if obs:
            result[obs_type] = ObservationSerializer(obs).data
    return Response({
        "zone": ZoneSerializer(zone).data,
        "latest": result,
    })
