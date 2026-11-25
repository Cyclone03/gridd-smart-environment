from collections.abc import Sequence
from datetime import datetime, timezone

from modules.ia.core.domain.collection_snapshot import CollectionSnapshot
from modules.ia.core.domain.weather_point import WeatherPoint
from modules.ia.core.domain.weather_snapshot import WeatherSnapshot
from modules.ia.core.inference.contract import INPUT_FEATURES


class DataCollectionService:
    """Collecte les mesures intérieures et la météo extérieure.

    Ports : ``WeatherSource`` (``weather``) et ``ObservationSource`` (``observations``).
    """

    def __init__(self, *, weather, observations, clock=None):
        self._weather = weather
        self._observations = observations
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def collect(self, zone_codes: Sequence[str] | None = None) -> CollectionSnapshot:
        return self.collect_with_weather(zone_codes, self.fetch_weather())

    def fetch_weather(self) -> WeatherSnapshot:
        return self._weather.fetch()

    def collect_with_weather(
        self,
        zone_codes: Sequence[str] | None,
        weather: WeatherSnapshot,
    ) -> CollectionSnapshot:
        zones = self._observations.fetch_latest(zone_codes)
        return CollectionSnapshot(
            collected_at=self._clock(),
            weather=weather,
            zones=zones,
        )

    @staticmethod
    def build_model_features(
        snapshot: CollectionSnapshot,
        zone_code: str,
        *,
        weather_point: WeatherPoint,
    ) -> dict[str, float]:
        """Build named inputs; the caller explicitly selects the weather timestamp."""
        try:
            zone = snapshot.zones[zone_code]
        except KeyError as exc:
            raise ValueError(f"No observations were collected for zone {zone_code!r}.") from exc
        if zone.zone_code != zone_code:
            raise ValueError(f"Observation zone code does not match {zone_code!r}.")

        values = {
            "indoor_temperature": zone.temperature.value,
            "indoor_humidity": zone.humidity.value,
            "outdoor_temperature": weather_point.temperature_c,
            "outdoor_humidity": weather_point.relative_humidity_pct,
        }
        return {feature: values[feature] for feature in INPUT_FEATURES}
