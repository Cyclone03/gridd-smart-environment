from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Sequence

from ..clients.gridd_api import GriddApiClient
from ..clients.open_meteo import OpenMeteoClient
from ..config import ServiceSettings
from ..domain.observations import ZoneObservations
from ..domain.weather import WeatherPoint, WeatherSnapshot
from ..models.contract import INPUT_FEATURES


@dataclass(frozen=True)
class CollectionSnapshot:
    collected_at: datetime
    weather: WeatherSnapshot
    zones: dict[str, ZoneObservations]


class DataCollectionService:
    def __init__(self, *, weather: OpenMeteoClient, observations: GriddApiClient):
        self._weather = weather
        self._observations = observations

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None):
        settings = ServiceSettings.from_env(environ)
        return cls(
            weather=OpenMeteoClient(
                settings.open_meteo_latitude,
                settings.open_meteo_longitude,
                timeout_seconds=settings.http_timeout_seconds,
            ),
            observations=GriddApiClient(
                settings.gridd_api_base_url,
                timeout_seconds=settings.http_timeout_seconds,
            ),
        )

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
            collected_at=datetime.now(timezone.utc),
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
