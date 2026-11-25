from typing import Protocol


class SensorReader(Protocol):
    """Lecture des capteurs actifs."""

    def active(self, zone_code=None): ...

    def get(self, sensor_id): ...
