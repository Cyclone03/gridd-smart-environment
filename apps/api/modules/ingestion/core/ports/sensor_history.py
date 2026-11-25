from typing import Protocol

from modules.ingestion.core.domain.past_reading import PastReading


class SensorHistory(Protocol):
    """Mesures récentes d'un capteur, la plus récente en premier."""

    def recent(self, node_id, metric) -> list[PastReading]: ...

    def record(self, node_id, metric, reading: PastReading) -> None:
        """Mémorise une mesure validée (peut être sans effet)."""
