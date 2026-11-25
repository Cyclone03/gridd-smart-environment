from typing import Protocol

from modules.ingestion.core.domain.known_sensor import KnownSensor


class KnownSensorReader(Protocol):
    """Capteur déjà enregistré pour ``(node_id, type)``, ou ``None``."""

    def find(self, node_id, metric) -> KnownSensor | None: ...
