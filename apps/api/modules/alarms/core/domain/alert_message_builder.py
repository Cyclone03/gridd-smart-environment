from shared.kernel.metrics import MetricCatalog
from shared.kernel.vocabulary import AlertSeverity, QualityStatus

from .condition_formatter import ConditionFormatter


class AlertMessageBuilder:
    """Messages et gravités des alertes."""

    MAX_LENGTH = 255

    def rule_message(self, rule, zone_name, value) -> str:
        definition = MetricCatalog.get(rule.metric)
        unit = definition.unit if definition else ""
        value_text = ConditionFormatter.format_number(value, bool(definition and definition.integer))
        condition = ConditionFormatter.describe_rule(rule.metric, rule.operator, rule.threshold, rule.threshold_high)
        return f"{rule.name} — {zone_name} : {value_text} {unit} (condition {condition})"[: self.MAX_LENGTH]

    def quality_message(self, status, reason, zone_name) -> str:
        label = QualityStatus.label(status).lower()
        return f"Donnée {label} pour {zone_name}: {reason}"[: self.MAX_LENGTH]

    @staticmethod
    def quality_severity(status) -> str:
        if status == QualityStatus.INVALID:
            return AlertSeverity.CRITICAL
        return AlertSeverity.WARNING
