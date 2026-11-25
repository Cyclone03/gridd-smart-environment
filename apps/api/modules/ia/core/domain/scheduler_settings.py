import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SchedulerSettings:
    """Planification des cycles.

    ``align_seconds`` / ``align_offset_seconds`` : chaque cycle démarre sur un
    créneau d'horloge (multiple de ``align_seconds`` + décalage). Open-Meteo
    publie ses conditions courantes par pas de 15 minutes (``current.time`` =
    début du quart d'heure) et l'orchestrateur refuse plus de 5 minutes d'écart
    avec les mesures intérieures : un cycle lancé à HH:07 ou HH:52 échouait
    donc pour toutes les zones, à chaque heure. Aligné juste après le quart
    d'heure, l'écart reste d'environ une minute. ``0`` = pas d'alignement.
    """

    interval_seconds: int = 3600
    heartbeat_interval_seconds: float = 30
    heartbeat_max_age_seconds: float = 180
    heartbeat_path: Path = Path("/var/lib/ai-predictions/heartbeat")
    align_seconds: float = 0
    align_offset_seconds: float = 0

    def __post_init__(self):
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive.")
        if (
            not math.isfinite(self.heartbeat_interval_seconds)
            or self.heartbeat_interval_seconds <= 0
        ):
            raise ValueError("heartbeat_interval_seconds must be positive and finite.")
        if (
            not math.isfinite(self.heartbeat_max_age_seconds)
            or self.heartbeat_max_age_seconds <= self.heartbeat_interval_seconds
        ):
            raise ValueError("heartbeat_max_age_seconds must exceed the heartbeat interval.")
        if not str(self.heartbeat_path).strip():
            raise ValueError("heartbeat_path must not be empty.")
        if not math.isfinite(self.align_seconds) or self.align_seconds < 0:
            raise ValueError("align_seconds must be zero or a positive finite number.")
        if self.align_seconds and not 0 <= self.align_offset_seconds < self.align_seconds:
            raise ValueError("align_offset_seconds must be between 0 and align_seconds.")
