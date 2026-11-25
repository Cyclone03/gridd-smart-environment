from typing import Protocol

from modules.alarms.core.domain.rule_snapshot import RuleSnapshot


class AlarmRuleReader(Protocol):
    """Lecture des règles d'alarme."""

    def search(self, *, zone=None, metric=None, enabled=None):
        """``zone`` : code de zone (règles de la zone et règles globales) ou ``"all"``."""

    def get(self, rule_id):
        """Règle (forme attendue par l'adaptateur HTTP) ou ``None``."""

    def active_for(self, zone_code, metric) -> list[RuleSnapshot]:
        """Règles actives applicables à une zone et un type de mesure."""
