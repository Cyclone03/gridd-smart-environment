from dataclasses import dataclass

from .weather_point import WeatherPoint


@dataclass(frozen=True)
class WeatherSnapshot:
    current: WeatherPoint
    forecast_h1: WeatherPoint
