from datetime import timedelta

from django.db.models.functions import Coalesce

from modules.database.models import Observation


class EnergyInputRepository:
    """Mesures utilisées par le modèle énergétique (lecture seule).

    Seules les mesures valides de température et d'occupation sont prises en compte.
    """

    INPUTS = ("temperature", "occupancy")

    def previous_moment(self, zone_code, *, before, exclude_id):
        row = self._inputs(zone_code).exclude(pk=exclude_id).filter(moment__lt=before).order_by("-moment").first()
        return row["moment"] if row else None

    def has_later(self, zone_code, *, after, exclude_id) -> bool:
        return self._inputs(zone_code).exclude(pk=exclude_id).filter(moment__gt=after).exists()

    def has_simultaneous_before(self, zone_code, *, moment, observation_id) -> bool:
        """Une autre mesure d'entrée du même instant, enregistrée avant celle-ci."""
        return self._inputs(zone_code).filter(moment=moment, pk__lt=observation_id).exists()

    def latest_value(self, zone_code, metric, *, at, max_age_minutes) -> float | None:
        row = (
            self._valid(zone_code)
            .filter(type=metric, moment__lte=at, moment__gte=at - timedelta(minutes=max_age_minutes))
            .order_by("-moment")
            .first()
        )
        return row["value"] if row else None

    def _inputs(self, zone_code):
        return self._valid(zone_code).filter(type__in=self.INPUTS)

    @staticmethod
    def _valid(zone_code):
        return (
            Observation.objects.filter(zone__code=zone_code)
            .exclude(quality_status=Observation.QualityStatus.INVALID)
            .annotate(moment=Coalesce("observed_at", "received_at"))
            .values("value", "moment")
        )
