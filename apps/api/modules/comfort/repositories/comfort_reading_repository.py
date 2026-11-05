from datetime import timedelta

from django.db.models.functions import Coalesce

from modules.database.models import Observation


class ComfortReadingRepository:
    """Dernière mesure valide d'une zone avant un instant (lecture seule)."""

    def latest_value(self, zone_code, metric, *, at, max_age_minutes) -> float | None:
        row = (
            Observation.objects.filter(zone__code=zone_code, type=metric)
            .exclude(quality_status=Observation.QualityStatus.INVALID)
            .annotate(moment=Coalesce("observed_at", "received_at"))
            .filter(moment__lte=at, moment__gte=at - timedelta(minutes=max_age_minutes))
            .order_by("-moment")
            .values("value")
            .first()
        )
        return row["value"] if row else None
