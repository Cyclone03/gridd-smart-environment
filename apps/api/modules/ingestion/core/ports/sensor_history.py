from typing import Protocol

from modules.ingestion.core.domain.past_reading import PastReading


class SensorHistory(Protocol):
    """Mesures récentes d'un capteur (identifiant zone + mesure), la plus
    récente en premier."""

    def recent(self, sensor, metric) -> list[PastReading]: ...

    def record(self, sensor, metric, reading: PastReading) -> None:
        """Mémorise une mesure validée (peut être sans effet)."""
