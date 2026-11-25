from dataclasses import dataclass
from datetime import datetime

from .weather_snapshot import WeatherSnapshot
from .zone_observations import ZoneObservations


@dataclass(frozen=True)
class CollectionSnapshot:
    collected_at: datetime
    weather: WeatherSnapshot
    zones: dict[str, ZoneObservations]
