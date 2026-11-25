from typing import Protocol


class RuleStateStore(Protocol):
    """États d'évaluation des règles d'alarme."""

    def save(self, *, rule_id, zone, status, pending_since, last_value, last_observed_at) -> bool: ...

    def reset_rule(self, rule_id) -> int: ...
