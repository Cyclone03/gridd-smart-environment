from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class WeatherPoint:
    timestamp_utc: datetime
    temperature_c: float
    relative_humidity_pct: float


@dataclass(frozen=True)
class WeatherSnapshot:
    current: WeatherPoint
    forecast_h1: WeatherPoint
