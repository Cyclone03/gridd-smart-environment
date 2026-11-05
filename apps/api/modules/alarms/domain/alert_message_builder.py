from modules.database.models import Alert, Observation
from shared.metrics.metric_catalog import MetricCatalog

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
        label = Observation.QualityStatus(status).label.lower()
        return f"Donnée {label} pour {zone_name}: {reason}"[: self.MAX_LENGTH]

    @staticmethod
    def quality_severity(status) -> str:
        if status == Observation.QualityStatus.INVALID:
            return Alert.Severity.CRITICAL
        return Alert.Severity.WARNING
