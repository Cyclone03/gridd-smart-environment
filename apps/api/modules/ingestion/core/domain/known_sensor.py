from dataclasses import dataclass


@dataclass(frozen=True)
class KnownSensor:
    """Capteur déjà enregistré, tel que vu par l'ingestion."""

    zone_code: str
    unit: str
    active: bool
