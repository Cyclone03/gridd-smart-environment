from modules.alarms.core.domain.alarm_rule_validator import AlarmRuleValidator
from shared.kernel.metrics import MetricCatalog, Operator
from shared.kernel.vocabulary import AlertSeverity


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
            "severities": [{"key": key, "label": label} for key, label in AlertSeverity.CHOICES],
            "max_duration_seconds": AlarmRuleValidator.MAX_DURATION_SECONDS,
        }
