from typing import Protocol

from modules.alarms.core.domain.rule_state import RuleState


class RuleStates(Protocol):
    """État d'évaluation de chaque (règle, zone), avec limitation des republications."""

    def get(self, rule_id, zone_code) -> RuleState: ...

    def remember(self, rule_id, zone_code, state: RuleState) -> None: ...

    def should_save(self, rule_id, zone_code, state: RuleState) -> bool: ...

    def should_refresh_alert(self, rule_id, zone_code, moment, *, triggered=False) -> bool: ...

    def forget_rule(self, rule_id) -> None: ...
