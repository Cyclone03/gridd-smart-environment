from typing import Protocol


class SensorSource(Protocol):
    """Capteurs à simuler (liste de ``SimulatedSensor``)."""

    def active(self) -> list: ...
