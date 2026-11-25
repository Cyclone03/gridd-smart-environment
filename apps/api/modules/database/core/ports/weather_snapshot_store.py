from typing import Protocol


class WeatherSnapshotStore(Protocol):
    """Instantanés météo, idempotents par ``event_id``."""

    def create(self, *, event_id, values) -> tuple[object, bool]: ...
