from shared.metrics.operator import Operator


class ConditionEvaluator:
    """Comparaison d'une valeur à la condition d'une règle (logique pure)."""

    @staticmethod
    def condition_met(operator, value, threshold, threshold_high=None) -> bool:
        """Indique si ``value`` est en situation d'alarme."""
        if operator == Operator.GT:
            return value > threshold
        if operator == Operator.GTE:
            return value >= threshold
        if operator == Operator.LT:
            return value < threshold
        if operator == Operator.LTE:
            return value <= threshold
        if operator == Operator.OUTSIDE_RANGE:
            return value < threshold or value > threshold_high
        if operator == Operator.INSIDE_RANGE:
            return threshold <= value <= threshold_high
        raise ValueError(f"Opérateur inconnu : {operator}")

    @classmethod
    def back_to_normal(cls, operator, value, threshold, threshold_high=None, hysteresis=0.0) -> bool:
        """Indique si une alarme active peut être résolue.

        L'hystérésis repousse le seuil de retour à la normale vers la zone
        saine : « > 30 » avec 1 d'hystérésis se résout à 29 ou moins ;
        « hors de [30 ; 60] » se résout entre 31 et 59.
        """
        h = hysteresis or 0.0
        if operator in (Operator.GT, Operator.GTE):
            return value <= threshold - h if h else not cls.condition_met(operator, value, threshold)
        if operator in (Operator.LT, Operator.LTE):
            return value >= threshold + h if h else not cls.condition_met(operator, value, threshold)
        if operator == Operator.OUTSIDE_RANGE:
            return threshold + h <= value <= threshold_high - h
        if operator == Operator.INSIDE_RANGE:
            return value < threshold - h or value > threshold_high + h
        raise ValueError(f"Opérateur inconnu : {operator}")
