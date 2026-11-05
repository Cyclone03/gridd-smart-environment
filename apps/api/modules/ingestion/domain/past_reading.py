from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PastReading:
    """Mesure antérieure d'un capteur, utilisée par le contrôle de qualité."""

    value: float
    observed_at: datetime | None
    received_at: datetime

    @property
    def moment(self) -> datetime:
        return self.observed_at or self.received_at
