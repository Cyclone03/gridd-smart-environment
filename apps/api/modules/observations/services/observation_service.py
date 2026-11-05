from modules.observations.repositories.observation_repository import ObservationRepository
from modules.observations.repositories.zone_repository import ZoneRepository
from shared.metrics.metric_catalog import MetricCatalog


class ObservationService:
    """Consultation des mesures : flux récent et dernières valeurs."""

    FEED_LIMIT = 1000

    def __init__(self, observations=None, zones=None):
        self._observations = observations or ObservationRepository()
        self._zones = zones or ZoneRepository()

    def feed(self, zone_code=None, metric=None):
        return self._observations.recent(zone_code=zone_code, metric=metric, limit=self.FEED_LIMIT)

    def get(self, observation_id):
        return self._observations.get(observation_id)

    def latest(self):
        """Dernière mesure de chaque zone active et de chaque type.

        Indépendant du flux limité à 1 000 lignes : un capteur très bavard ne
        doit pas masquer une mesure moins fréquente.
        """
        observations = [
            observation
            for zone in self._observations.active_zones()
            for metric in MetricCatalog.keys()
            if (observation := self._observations.latest(zone, metric)) is not None
        ]
        return sorted(observations, key=lambda item: item.observed_at or item.received_at, reverse=True)

    def latest_for_zone(self, zone_code):
        """``(zone, {type: observation})`` ou ``None`` si la zone est inconnue."""
        zone = self._zones.get_by_code(zone_code)
        if zone is None:
            return None
        latest = {}
        for metric in MetricCatalog.keys():
            observation = self._observations.latest(zone, metric)
            if observation is not None:
                latest[metric] = observation
        return zone, latest
