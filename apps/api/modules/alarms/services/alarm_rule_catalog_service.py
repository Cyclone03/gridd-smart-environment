from modules.alarms.domain.alarm_rule_validator import AlarmRuleValidator
from modules.database.models import Alert
from shared.metrics.metric_catalog import MetricCatalog
from shared.metrics.operator import Operator


class AlarmRuleCatalogService:
    """Catalogue utilisé par le formulaire : mesures, opérateurs, gravités."""

    def describe(self) -> dict:
        return {
            "metrics": [
                {
                    "key": definition.key,
                    "label": definition.label,
                    "unit": definition.unit,
                    "integer": definition.integer,
                    "min": definition.plausible_range[0] if definition.plausible_range else None,
                    "max": definition.plausible_range[1] if definition.plausible_range else None,
                    "operators": list(definition.operators),
                }
                for definition in MetricCatalog.definitions()
            ],
            "operators": [
                {
                    "key": key,
                    "label": Operator.LABELS[key],
                    "symbol": Operator.SYMBOLS.get(key),
                    "range": Operator.is_range(key),
                }
                for key in Operator.ALL
            ],
            "severities": [{"key": key, "label": label} for key, label in Alert.Severity.choices],
            "max_duration_seconds": AlarmRuleValidator.MAX_DURATION_SECONDS,
        }
