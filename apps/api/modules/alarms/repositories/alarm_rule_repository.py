from django.db.models import Count, Q

from modules.alarms.domain.rule_snapshot import RuleSnapshot
from modules.database.models import AlarmRule


class AlarmRuleRepository:
    """Lecture des règles d'alarme (lecture seule)."""

    def search(self, *, zone=None, metric=None, enabled=None):
        """``zone`` : code de zone (règles de la zone et règles globales) ou ``"all"`` (globales seules)."""
        rules = self._annotated()
        if zone == "all":
            rules = rules.filter(zone__isnull=True)
        elif zone:
            rules = rules.filter(Q(zone__code=zone) | Q(zone__isnull=True))
        if metric:
            rules = rules.filter(metric=metric)
        if enabled is not None:
            rules = rules.filter(enabled=enabled)
        return rules

    def get(self, rule_id) -> AlarmRule | None:
        try:
            return self._annotated().filter(pk=int(rule_id)).first()
        except (TypeError, ValueError):
            return None

    def active_for(self, zone_code, metric) -> list[RuleSnapshot]:
        rules = AlarmRule.objects.filter(enabled=True, metric=metric).filter(
            Q(zone__code=zone_code) | Q(zone__isnull=True)
        )
        return [
            RuleSnapshot(
                id=rule.pk,
                name=rule.name,
                metric=rule.metric,
                operator=rule.operator,
                threshold=rule.threshold,
                threshold_high=rule.threshold_high,
                severity=rule.severity,
                min_duration_seconds=rule.min_duration_seconds,
                hysteresis=rule.hysteresis,
            )
            for rule in rules
        ]

    @staticmethod
    def _annotated():
        return AlarmRule.objects.select_related("zone", "created_by", "updated_by").annotate(
            active_alerts=Count("alerts", filter=Q(alerts__active=True)),
        )
