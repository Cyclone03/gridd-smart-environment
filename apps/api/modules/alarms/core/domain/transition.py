from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Transition:
    status: str
    pending_since: datetime | None
    # "triggered", "resolved", "ongoing" (alarme maintenue) ou None.
    event: str | None
