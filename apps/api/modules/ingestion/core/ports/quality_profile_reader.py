from typing import Protocol

from modules.ingestion.core.domain.quality_profile import QualityProfile


class QualityProfileReader(Protocol):
    """Paramètres de contrôle de qualité d'une zone, ou ``None``."""

    def for_zone(self, zone_code) -> QualityProfile | None: ...
