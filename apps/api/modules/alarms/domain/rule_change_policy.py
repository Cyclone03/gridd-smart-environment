from modules.database.models import Alert

from .rule_change_decision import RuleChangeDecision


class RuleChangePolicy:
    """Effets d'une modification de règle (logique pure).

    - suppression : alertes en cours résolues (« règle supprimée ») ;
    - désactivation : alertes en cours résolues (« règle désactivée ») ;
    - modification de la condition : alertes résolues (« règle modifiée »),
      la règle est réévaluée à la mesure suivante ;
    - changement de gravité seul : reporté sur les alertes en cours.
    """

    CONDITION_FIELDS = frozenset(
        {"zone", "metric", "operator", "threshold", "threshold_high", "min_duration_seconds", "hysteresis"}
    )

    def decide(self, action, changed_fields, enabled) -> RuleChangeDecision:
        if action == "deleted":
            return RuleChangeDecision(resolution=Alert.Resolution.RULE_DELETED)
        if action != "updated":
            return RuleChangeDecision()
        changed = set(changed_fields)
        if "enabled" in changed and not enabled:
            return RuleChangeDecision(resolution=Alert.Resolution.RULE_DISABLED)
        if self.CONDITION_FIELDS & changed:
            return RuleChangeDecision(resolution=Alert.Resolution.RULE_UPDATED)
        if "severity" in changed:
            return RuleChangeDecision(propagate_severity=True)
        return RuleChangeDecision()
