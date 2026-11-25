from dataclasses import dataclass
from datetime import datetime

from .alarm_status import AlarmStatus


@dataclass(frozen=True)
class RuleState:
    """État d'évaluation d'une règle pour une zone."""

    status: str
    pending_since: datetime | None = None
    last_value: float | None = None
    last_observed_at: datetime | None = None

    @classmethod
    def initial(cls) -> "RuleState":
        return cls(status=AlarmStatus.NORMAL)
