from typing import Protocol


class WeatherSnapshotReader(Protocol):
    """Dernier instantané météo."""

    def latest(self): ...
