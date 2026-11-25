from typing import Protocol

from modules.ia.core.domain.weather_snapshot import WeatherSnapshot


class WeatherSource(Protocol):
    """Conditions extérieures actuelles et prévision à H+1."""

    def fetch(self) -> WeatherSnapshot: ...
