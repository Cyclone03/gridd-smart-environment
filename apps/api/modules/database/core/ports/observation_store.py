from typing import Protocol


class ObservationStore(Protocol):
    """Insertion groupée et idempotente (par ``event_id``) des observations."""

    def create_many(self, items) -> list:
        """``items`` : ``(payload, zone, sensor)`` ; retourne les observations créées."""
