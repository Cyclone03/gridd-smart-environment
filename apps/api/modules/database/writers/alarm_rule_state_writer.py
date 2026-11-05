from django.utils.dateparse import parse_datetime

from modules.database.models import AlarmRule, AlarmRuleState


class AlarmRuleStateWriter:
    """Persistance de l'état d'évaluation des règles par zone."""

    def save(self, *, rule_id, zone, status, pending_since, last_value, last_observed_at) -> bool:
        if not AlarmRule.objects.filter(pk=rule_id).exists():
            return False  # règle supprimée entre-temps
        AlarmRuleState.objects.update_or_create(
            rule_id=rule_id,
            zone=zone,
            defaults={
                "status": status,
                "pending_since": parse_datetime(pending_since) if pending_since else None,
                "last_value": last_value,
                "last_observed_at": parse_datetime(last_observed_at) if last_observed_at else None,
            },
        )
        return True

    def reset_rule(self, rule_id) -> int:
        deleted, _ = AlarmRuleState.objects.filter(rule_id=rule_id).delete()
        return deleted
