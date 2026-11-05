from datetime import timedelta

from modules.database.models import AlarmRuleState

from .transition import Transition

Status = AlarmRuleState.Status


class AlarmStateMachine:
    """Cycle de vie d'une règle pour une zone (logique pure).

        NORMAL ──condition vraie──► PENDING ──durée minimale atteinte──► ACTIVE
           ▲            │ (durée 0 : passage direct à ACTIVE)               │
           └─condition fausse─┘                                             │
           ▲                                                                │
           └──────────── retour à la normale (avec hystérésis) ◄────────────┘
    """

    TRIGGERED = "triggered"
    RESOLVED = "resolved"
    ONGOING = "ongoing"

    def next(self, status, pending_since, *, breached, cleared, observed_at, min_duration_seconds) -> Transition:
        if status == Status.ACTIVE:
            if cleared:
                return Transition(Status.NORMAL, None, self.RESOLVED)
            return Transition(Status.ACTIVE, None, self.ONGOING)

        if not breached:
            return Transition(Status.NORMAL, None, None)

        if min_duration_seconds <= 0:
            return Transition(Status.ACTIVE, None, self.TRIGGERED)

        started = pending_since if status == Status.PENDING and pending_since else observed_at
        if observed_at - started >= timedelta(seconds=min_duration_seconds):
            return Transition(Status.ACTIVE, None, self.TRIGGERED)
        return Transition(Status.PENDING, started, None)
