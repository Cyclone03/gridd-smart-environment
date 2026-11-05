from dataclasses import dataclass
from datetime import datetime

from modules.database.models import AlarmRuleState


@dataclass(frozen=True)
class RuleState:
    """État d'évaluation d'une règle pour une zone."""

    status: str
    pending_since: datetime | None = None
    last_value: float | None = None
    last_observed_at: datetime | None = None

    @classmethod
    def initial(cls) -> "RuleState":
        return cls(status=AlarmRuleState.Status.NORMAL)
