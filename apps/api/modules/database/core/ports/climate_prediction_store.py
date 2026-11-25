from typing import Protocol


class ClimatePredictionStore(Protocol):
    """Prédictions climatiques, idempotentes par ``event_id``."""

    def create(self, *, event_id, zone, values) -> tuple[object, bool]: ...
