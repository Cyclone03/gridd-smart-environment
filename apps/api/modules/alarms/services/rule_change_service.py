from modules.alarms.domain.alert_codes import AlertCodes


class RuleChangeService:
    """Tire les conséquences d'une règle créée, modifiée ou supprimée
    (événement ``alarm_rule.changed`` publié par le module Database)."""

    def __init__(self, *, states, producer, policy):
        self._states = states
        self._producer = producer
        self._policy = policy

    def apply(self, change):
        rule_id = change["rule_id"]
        decision = self._policy.decide(change["action"], change.get("changed_fields") or [], change.get("enabled"))
        if decision.resolution:
            self._states.forget_rule(rule_id)
            self._producer.rule_reset(rule_id=rule_id, alert_code=AlertCodes.for_rule(rule_id), resolution=decision.resolution)
        elif decision.propagate_severity:
            self._producer.severity_propagated(
                rule_id=rule_id,
                alert_code=AlertCodes.for_rule(rule_id),
                severity=change["severity"],
            )
        return decision
