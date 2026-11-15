from django.utils import timezone

from shared.metrics.metric_catalog import MetricCatalog


class DashboardPayloadMapper:
    """Représentation JSON envoyée sur le WebSocket.

    Mêmes formes que l'API REST (``/api/zones/``, ``/api/observations/latest/``,
    ``/api/alerts/``) : le frontend utilise les mêmes types dans les deux cas.
    """

    PROFILE_EXCLUDED_FIELDS = {"id", "zone"}

    def zone(self, zone) -> dict:
        sensors = getattr(zone, "active_sensors", None)
        if sensors is None:
            sensors = zone.sensors.filter(active=True)
        return {
            "id": zone.pk,
            "name": zone.name,
            "code": zone.code,
            "zone_type": zone.zone_type,
            "description": zone.description,
            "active": zone.active,
            "metrics": sorted({sensor.sensor_type for sensor in sensors}, key=MetricCatalog.position),
            "threshold_profile": self._profile(zone),
        }

    def observation(self, observation) -> dict:
        return {
            "id": observation.pk,
            "zone": observation.zone_id,
            "zone_code": observation.zone.code,
            "zone_name": observation.zone.name,
            "sensor": observation.sensor_id,
            "sensor_node_id": observation.sensor.node_id,
            "type": observation.type,
            "value": observation.value,
            "unit": observation.unit,
            "observed_at": self._instant(observation.observed_at),
            "received_at": self._instant(observation.received_at),
            "quality_status": observation.quality_status,
            "quality_reason": observation.quality_reason,
            "metadata": observation.metadata,
        }

    def alert(self, alert) -> dict:
        return {
            "id": alert.pk,
            "zone": alert.zone_id,
            "zone_code": alert.zone.code,
            "zone_name": alert.zone.name,
            "observation": alert.observation_id,
            "rule": alert.rule_id,
            "rule_name": alert.rule.name if alert.rule_id else None,
            "code": alert.code,
            "message": alert.message,
            "severity": alert.severity,
            "trigger_value": alert.trigger_value,
            "created_at": self._instant(alert.created_at),
            "resolved_at": self._instant(alert.resolved_at),
            "resolution": alert.resolution,
            "active": alert.active,
        }

    def _profile(self, zone):
        try:
            profile = zone.threshold_profile
        except zone.__class__.threshold_profile.RelatedObjectDoesNotExist:
            return None
        return {
            field.name: getattr(profile, field.name)
            for field in profile._meta.concrete_fields
            if field.name not in self.PROFILE_EXCLUDED_FIELDS
        }

    @staticmethod
    def _instant(value):
        return timezone.localtime(value).isoformat() if value else None
