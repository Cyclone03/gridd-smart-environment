from django.db.models import F

from modules.database.models import Observation, Zone
from modules.ia.core.domain.metric_observation import MetricObservation
from modules.ia.core.domain.zone_observations import ZoneObservations
from modules.ia.core.errors import IncompleteObservationsError, UnknownZoneError


class DatabaseObservationSource:
    """Adaptateur Django du port ``ObservationSource`` : lit directement le
    schéma du module Database (lecture seule), mêmes règles que
    ``/api/observations/latest/`` (mesure la plus récente par horodatage
    capteur, puis de réception)."""

    METRICS = ("temperature", "humidity")

    def fetch_latest(self, zone_codes=None) -> dict[str, ZoneObservations]:
        zones = {zone.code: zone for zone in Zone.objects.filter(active=True)}
        if not zones:
            raise IncompleteObservationsError("No active zone is registered.")
        requested = list(zones) if zone_codes is None else self._requested(zone_codes)
        unknown = [code for code in requested if code not in zones]
        if unknown:
            raise UnknownZoneError(f"Unknown or inactive zone code(s): {', '.join(unknown)}.")

        result = {}
        for code in requested:
            latest = {metric: self._latest(zones[code], metric) for metric in self.METRICS}
            missing = [metric for metric, observation in latest.items() if observation is None]
            if missing:
                raise IncompleteObservationsError(f"Zone {code} is missing latest observation(s): {', '.join(missing)}.")
            result[code] = ZoneObservations(zone_code=code, temperature=latest["temperature"], humidity=latest["humidity"])
        return result

    @staticmethod
    def _requested(zone_codes):
        if isinstance(zone_codes, str):
            raise ValueError("zone_codes must be a sequence of codes, not a string.")
        codes = list(zone_codes)
        if not codes or len(codes) != len(set(codes)) or any(not isinstance(code, str) or not code for code in codes):
            raise ValueError("zone_codes must contain distinct, non-empty zone codes.")
        return codes

    @staticmethod
    def _latest(zone, metric) -> MetricObservation | None:
        row = (
            Observation.objects.filter(zone=zone, type=metric)
            .order_by(F("observed_at").desc(nulls_last=True), "-received_at")
            .values("value", "unit", "observed_at", "received_at", "quality_status")
            .first()
        )
        if row is None:
            return None
        return MetricObservation(
            value=float(row["value"]),
            unit=row["unit"],
            observed_at=row["observed_at"],
            received_at=row["received_at"],
            quality_status=row["quality_status"],
        )
