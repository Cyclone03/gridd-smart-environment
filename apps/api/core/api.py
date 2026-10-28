"""Points d'accès REST en lecture : zones, capteurs, observations, alertes,
historique et état de santé. Voir docs/api.md pour le contrat complet."""

from django.conf import settings
from django.db import connection
from django.db.models import F, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from . import metrics
from .history import HistoryParamError, aggregate, compute_trend, parse_period
from .models import Alert, Observation, Sensor, Zone
from .serializers import AlertSerializer, ObservationSerializer, SensorSerializer, ZoneSerializer


def _newest_first(queryset):
    return queryset.order_by(F("observed_at").desc(nulls_last=True), "-received_at")


class ZoneViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ZoneSerializer

    def get_queryset(self):
        return (
            Zone.objects.filter(active=True)
            .select_related("threshold_profile")
            .prefetch_related(
                Prefetch(
                    "sensors",
                    queryset=Sensor.objects.filter(active=True),
                    to_attr="active_sensors",
                )
            )
            .order_by("name")
        )


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
        return _newest_first(qs)[:1000]

    @action(detail=False, methods=["get"], url_path="latest")
    def latest(self, request):
        """Dernière mesure disponible pour chaque zone active et chaque type.

        Volontairement indépendant du flux global limité à 1 000 lignes : un
        capteur très bavard ne doit pas masquer une mesure moins fréquente.
        """
        observations = []
        for zone in Zone.objects.filter(active=True).order_by("name"):
            for metric_type in metrics.METRICS:
                observation = _newest_first(
                    Observation.objects.filter(zone=zone, type=metric_type).select_related("zone", "sensor")
                ).first()
                if observation:
                    observations.append(observation)

        observations.sort(
            key=lambda observation: observation.observed_at or observation.received_at,
            reverse=True,
        )
        return Response(ObservationSerializer(observations, many=True).data)


def _parse_instant_param(request, name):
    raw = request.query_params.get(name)
    if not raw:
        return None
    value = parse_datetime(raw)
    if value is None:
        raise ValidationError({name: ["Date et heure ISO 8601 attendue."]})
    if timezone.is_naive(value):
        value = timezone.make_aware(value)
    return value


class AlertViewSet(viewsets.ReadOnlyModelViewSet):
    """Alertes et historique des événements d'alarme.

    Chaque alerte est un épisode : ``created_at`` (déclenchement) puis
    ``resolved_at`` / ``resolution`` (retour à la normale). Filtres :
    ``active``, ``zone`` (code), ``rule`` (id), ``severity``, ``since``,
    ``until`` (ISO 8601) et ``limit`` (défaut 500, maximum 1 000).
    """

    serializer_class = AlertSerializer

    def get_queryset(self):
        qs = Alert.objects.select_related("zone", "observation", "rule")
        params = self.request.query_params
        if params.get("zone"):
            qs = qs.filter(zone__code=params["zone"])
        if params.get("active") in {"true", "false"}:
            qs = qs.filter(active=(params["active"] == "true"))
        if params.get("rule"):
            try:
                qs = qs.filter(rule_id=int(params["rule"]))
            except ValueError as exc:
                raise ValidationError({"rule": ["Identifiant de règle invalide."]}) from exc
        if params.get("severity"):
            qs = qs.filter(severity=params["severity"])
        since = _parse_instant_param(self.request, "since")
        until = _parse_instant_param(self.request, "until")
        if since:
            qs = qs.filter(created_at__gte=since)
        if until:
            qs = qs.filter(created_at__lte=until)
        if self.action != "list":
            return qs
        try:
            limit = min(max(int(params.get("limit", "500")), 1), 1000)
        except ValueError as exc:
            raise ValidationError({"limit": ["Nombre entier attendu."]}) from exc
        return qs.order_by("-created_at")[:limit]


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Contrôle de santé utilisé par Docker et la supervision.

    Répond 200 si la base de données répond, 503 sinon.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        database = "connected"
        status = "ok"
    except Exception:
        database = "error"
        status = "degraded"

    channel_backend = settings.CHANNEL_LAYERS["default"]["BACKEND"].rsplit(".", 1)[-1]
    return Response(
        {
            "status": status,
            "database": database,
            "channel_layer": channel_backend,
            "timestamp": timezone.now().isoformat(),
        },
        status=200 if status == "ok" else 503,
    )


@api_view(["GET"])
def latest_by_zone(request, zone_code):
    zone = get_object_or_404(Zone, code=zone_code, active=True)
    result = {}
    for obs_type in metrics.METRICS:
        obs = _newest_first(Observation.objects.filter(zone=zone, type=obs_type).select_related("sensor", "zone")).first()
        if obs:
            result[obs_type] = ObservationSerializer(obs).data
    return Response({"zone": ZoneSerializer(zone).data, "latest": result})


@api_view(["GET"])
def zone_history(request, zone_code):
    """Historique agrégé d'une mesure pour une zone sur une période.

    Voir ``core.history`` pour les paramètres acceptés.
    """
    zone = get_object_or_404(Zone, code=zone_code, active=True)
    observation_type = request.query_params.get("type", "temperature")
    definition = metrics.get_metric(observation_type)
    if definition is None:
        return Response(
            {"detail": "Type de mesure invalide.", "errors": {"type": ["Type de mesure inconnu."]}},
            status=400,
        )

    tz = timezone.get_current_timezone()
    try:
        period = parse_period(request.query_params, tz=tz)
    except HistoryParamError as exc:
        body = {"detail": exc.message}
        if exc.field:
            body["errors"] = {exc.field: [exc.message]}
        return Response(body, status=400)

    in_period = Q(observed_at__gte=period.start, observed_at__lt=period.end) | Q(
        observed_at__isnull=True,
        received_at__gte=period.start,
        received_at__lt=period.end,
    )
    rows = (
        Observation.objects.filter(zone=zone, type=observation_type)
        .filter(in_period)
        .order_by("observed_at", "received_at")
        .values("value", "observed_at", "received_at", "quality_status")
        .iterator(chunk_size=5000)
    )
    points, values = aggregate(rows, period.bucket_minutes, tz, Observation.QualityStatus.NORMAL)

    return Response(
        {
            "zone_code": zone.code,
            "type": observation_type,
            "start": timezone.localtime(period.start, tz).isoformat(),
            "end": timezone.localtime(period.end, tz).isoformat(),
            "timezone": str(tz),
            "hours": period.hours,
            "date": period.date,
            "bucket_minutes": period.bucket_minutes,
            "unit": definition.unit,
            "points": points,
            "statistics": {
                "minimum": min(values) if values else None,
                "maximum": max(values) if values else None,
                "average": round(sum(values) / len(values), 2) if values else None,
                "count": len(values),
                "trend": compute_trend(points, definition.trend_tolerance),
            },
        }
    )
