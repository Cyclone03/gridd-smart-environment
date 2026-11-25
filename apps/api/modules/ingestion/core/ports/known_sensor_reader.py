from typing import Protocol

from modules.ingestion.core.domain.known_sensor import KnownSensor


class KnownSensorReader(Protocol):
    """Capteur déjà enregistré, ou ``None``. ``sensor`` : identifiant zone +
    mesure (``shared.kernel.sensor_identity.sensor_key``)."""

    def find(self, sensor, metric) -> KnownSensor | None: ...
