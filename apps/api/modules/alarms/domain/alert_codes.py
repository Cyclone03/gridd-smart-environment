class AlertCodes:
    """Codes d'alerte : origine d'un épisode, unique par zone tant qu'il est actif."""

    @staticmethod
    def for_rule(rule_id) -> str:
        return f"RULE_{rule_id}"

    @staticmethod
    def for_quality(metric) -> str:
        return f"DATA_QUALITY_{metric.upper()}"
