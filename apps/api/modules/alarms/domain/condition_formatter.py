from shared.metrics.metric_catalog import MetricCatalog
from shared.metrics.operator import Operator


class ConditionFormatter:
    """Libellés lisibles des conditions, ex. « > 30 °C » ou « hors de [30 ; 60] % »."""

    @staticmethod
    def format_number(value, integer=False) -> str:
        if integer:
            return str(int(round(value)))
        text = f"{value:.2f}".rstrip("0").rstrip(".")
        return text.replace(".", ",")

    @classmethod
    def describe(cls, operator, threshold, threshold_high, unit, integer=False) -> str:
        low = cls.format_number(threshold, integer)
        suffix = f" {unit}" if unit else ""
        if operator in Operator.SYMBOLS:
            return f"{Operator.SYMBOLS[operator]} {low}{suffix}"
        high = cls.format_number(threshold_high, integer)
        if operator == Operator.OUTSIDE_RANGE:
            return f"hors de [{low} ; {high}]{suffix}"
        return f"dans [{low} ; {high}]{suffix}"

    @classmethod
    def describe_rule(cls, metric, operator, threshold, threshold_high) -> str:
        definition = MetricCatalog.get(metric)
        return cls.describe(
            operator,
            threshold,
            threshold_high,
            definition.unit if definition else "",
            integer=bool(definition and definition.integer),
        )
