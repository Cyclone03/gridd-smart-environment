from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Sequence

from ..clients.gridd_api import GriddApiClient
from ..clients.open_meteo import OpenMeteoClient
from ..config import ServiceSettings
from ..domain.observations import ZoneObservations
from ..domain.weather import WeatherSnapshot


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
        weather = self._weather.fetch()
        zones = self._observations.fetch_latest(zone_codes)
        return CollectionSnapshot(
            collected_at=datetime.now(timezone.utc),
            weather=weather,
            zones=zones,
        )
