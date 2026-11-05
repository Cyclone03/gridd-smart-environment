from django.db.models import Q

from modules.database.models import Observation, Zone


class HistoryRepository:
    """Lecture des mesures d'une zone sur une période (lecture seule)."""

    def active_zone(self, code) -> Zone | None:
        return Zone.objects.filter(code=code, active=True).first()

    def rows(self, zone, metric, period):
        """Mesures dont l'horodatage capteur (ou de réception, à défaut) est
        dans ``[start ; end[``, triées chronologiquement."""
        in_period = Q(observed_at__gte=period.start, observed_at__lt=period.end) | Q(
            observed_at__isnull=True,
            received_at__gte=period.start,
            received_at__lt=period.end,
        )
        return (
            Observation.objects.filter(zone=zone, type=metric)
            .filter(in_period)
            .order_by("observed_at", "received_at")
            .values("value", "observed_at", "received_at", "quality_status")
            .iterator(chunk_size=5000)
        )
