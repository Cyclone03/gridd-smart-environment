from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MetricObservation:
    value: float
    unit: str
    observed_at: datetime | None
    received_at: datetime
    quality_status: str

    @property
    def effective_at(self) -> datetime:
        return self.observed_at or self.received_at
