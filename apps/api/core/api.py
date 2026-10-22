from datetime import datetime, time, timedelta

from django.db import connection
from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import action, api_view
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
        return qs.order_by(
            F("observed_at").desc(nulls_last=True),
            "-received_at",
        )[:1000]

    @action(detail=False, methods=["get"], url_path="latest")
    def latest(self, request):
        """Return the newest available reading for every active zone and metric.

        This endpoint is intentionally independent from the global 1,000-row
        activity feed. A noisy sensor must not hide a less frequent metric.
        """
        observations = []
        metric_types = [choice for choice, _ in Sensor.SensorType.choices]
        for zone in Zone.objects.filter(active=True).order_by("name"):
            for metric_type in metric_types:
                observation = (
                    Observation.objects
                    .filter(zone=zone, type=metric_type)
                    .select_related("zone", "sensor")
                    .order_by(
                        F("observed_at").desc(nulls_last=True),
                        "-received_at",
                    )
                    .first()
                )
                if observation:
                    observations.append(observation)

        observations.sort(
            key=lambda observation: observation.observed_at or observation.received_at,
            reverse=True,
        )
        return Response(ObservationSerializer(observations, many=True).data)


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
    for obs_type in ["temperature", "humidity", "sound_level", "occupancy"]:
        obs = (
            Observation.objects
            .filter(zone=zone, type=obs_type)
            .select_related("sensor")
            .order_by(
                F("observed_at").desc(nulls_last=True),
                "-received_at",
            )
            .first()
        )
        if obs:
            result[obs_type] = ObservationSerializer(obs).data
    return Response({
        "zone": ZoneSerializer(zone).data,
        "latest": result,
    })


@api_view(["GET"])
def zone_history(request, zone_code):
    zone = get_object_or_404(Zone, code=zone_code, active=True)
    observation_type = request.query_params.get("type", "temperature")
    valid_types = {choice for choice, _ in Sensor.SensorType.choices}
    if observation_type not in valid_types:
        return Response({"detail": "Type de mesure invalide."}, status=400)

    requested_date = request.query_params.get("date")
    if requested_date:
        try:
            selected_date = datetime.strptime(requested_date, "%Y-%m-%d").date()
        except ValueError:
            return Response({"detail": "La date doit respecter le format AAAA-MM-JJ."}, status=400)
        local_timezone = timezone.get_current_timezone()
        period_start = timezone.make_aware(
            datetime.combine(selected_date, time.min),
            local_timezone,
        )
        period_end = period_start + timedelta(days=1)
        hours = 24
        bucket_minutes = 15
        date_filter = (
            Q(observed_at__gte=period_start, observed_at__lt=period_end)
            | Q(
                observed_at__isnull=True,
                received_at__gte=period_start,
                received_at__lt=period_end,
            )
        )
    else:
        try:
            hours = int(request.query_params.get("hours", "24"))
        except ValueError:
            return Response({"detail": "La période doit être un nombre d'heures."}, status=400)
        if hours not in {1, 6, 24, 168}:
            return Response({"detail": "Période permise: 1, 6, 24 ou 168 heures."}, status=400)
        bucket_minutes = 5 if hours <= 6 else 15 if hours <= 24 else 60
        cutoff = timezone.now() - timedelta(hours=hours)
        date_filter = (
            Q(observed_at__gte=cutoff)
            | Q(observed_at__isnull=True, received_at__gte=cutoff)
        )

    observations = list(
        Observation.objects.filter(zone=zone, type=observation_type)
        .filter(date_filter)
        .order_by("observed_at", "received_at")
        .values("value", "unit", "observed_at", "received_at", "quality_status")
    )

    buckets = {}
    for observation in observations:
        measured_at = observation["observed_at"] or observation["received_at"]
        bucket_epoch = int(measured_at.timestamp()) // (bucket_minutes * 60)
        bucket_time = datetime.fromtimestamp(
            bucket_epoch * bucket_minutes * 60,
            tz=measured_at.tzinfo,
        )
        bucket = buckets.setdefault(
            bucket_epoch,
            {"time": bucket_time, "values": [], "suspicious": 0},
        )
        bucket["values"].append(float(observation["value"]))
        if observation["quality_status"] != Observation.QualityStatus.NORMAL:
            bucket["suspicious"] += 1

    points = []
    for bucket_epoch in sorted(buckets):
        bucket = buckets[bucket_epoch]
        values = bucket["values"]
        points.append({
            "time": bucket["time"].isoformat(),
            "average": round(sum(values) / len(values), 2),
            "minimum": min(values),
            "maximum": max(values),
            "count": len(values),
            "suspicious_count": bucket["suspicious"],
        })

    values = [float(observation["value"]) for observation in observations]
    trend = "stable"
    if len(points) >= 2:
        delta = points[-1]["average"] - points[0]["average"]
        tolerance = {
            "temperature": 0.2,
            "humidity": 1,
            "sound_level": 1,
            "occupancy": 1,
        }[observation_type]
        if delta > tolerance:
            trend = "rising"
        elif delta < -tolerance:
            trend = "falling"

    return Response({
        "zone_code": zone.code,
        "type": observation_type,
        "hours": hours,
        "date": requested_date,
        "bucket_minutes": bucket_minutes,
        "unit": observations[-1]["unit"] if observations else "",
        "points": points,
        "statistics": {
            "minimum": min(values) if values else None,
            "maximum": max(values) if values else None,
            "average": round(sum(values) / len(values), 2) if values else None,
            "count": len(values),
            "trend": trend,
        },
    })
