from collections.abc import Sequence
from typing import Protocol

from modules.ia.core.domain.zone_observations import ZoneObservations


class ObservationSource(Protocol):
    """Dernières mesures intérieures (température et humidité) par zone active.

    Lève ``UnknownZoneError`` pour une zone inconnue ou inactive et
    ``IncompleteObservationsError`` si une mesure manque.
    """

    def fetch_latest(self, zone_codes: Sequence[str] | None = None) -> dict[str, ZoneObservations]: ...
