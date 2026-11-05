from django.db.models import F

from modules.database.models import Observation, Zone


class ObservationRepository:
    """Lecture des observations (lecture seule)."""

    def recent(self, *, zone_code=None, metric=None, limit=1000):
        observations = Observation.objects.select_related("zone", "sensor")
        if zone_code:
            observations = observations.filter(zone__code=zone_code)
        if metric:
            observations = observations.filter(type=metric)
        return self._newest_first(observations)[:limit]

    def latest(self, zone, metric) -> Observation | None:
        return self._newest_first(
            Observation.objects.filter(zone=zone, type=metric).select_related("zone", "sensor")
        ).first()

    def active_zones(self):
        return Zone.objects.filter(active=True).order_by("name")

    def get(self, observation_id) -> Observation | None:
        try:
            return Observation.objects.select_related("zone", "sensor").filter(pk=int(observation_id)).first()
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _newest_first(observations):
        return observations.order_by(F("observed_at").desc(nulls_last=True), "-received_at")
