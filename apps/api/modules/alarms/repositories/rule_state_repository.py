from modules.alarms.domain.rule_state import RuleState
from modules.database.models import AlarmRuleState


class RuleStateRepository:
    """Lecture des états d'évaluation persistés (lecture seule)."""

    def get(self, rule_id, zone_code) -> RuleState | None:
        state = AlarmRuleState.objects.filter(rule_id=rule_id, zone__code=zone_code).first()
        if state is None:
            return None
        return RuleState(
            status=state.status,
            pending_since=state.pending_since,
            last_value=state.last_value,
            last_observed_at=state.last_observed_at,
        )
