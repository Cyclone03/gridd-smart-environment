from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Period:
    start: datetime
    end: datetime
    bucket_minutes: int
    # Valeurs renvoyées pour compatibilité avec l'ancien contrat.
    hours: int
    date: str | None = None

    @property
    def span(self):
        return self.end - self.start
