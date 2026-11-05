from shared.metrics.metric_catalog import MetricCatalog
from shared.metrics.operator import Operator


class AlarmRuleValidator:
    """Règles de validité d'une règle d'alarme (logique pure).

    - opérateur autorisé pour la mesure ;
    - intervalle : borne haute obligatoire et supérieure à la borne basse ;
      hystérésis inférieure à la moitié de l'intervalle pour « en dehors » ;
    - seuils dans les limites physiques du capteur ;
    - comptage (occupation) : seuils et hystérésis entiers ;
    - hystérésis positive ou nulle.
    """

    MAX_DURATION_SECONDS = 86400

    def name_error(self, name) -> str | None:
        return None if name.strip() else "Le nom est obligatoire."

    def metric_error(self, metric) -> str | None:
        return None if MetricCatalog.get(metric) else "Type de mesure inconnu."

    def validate(self, attrs, current) -> tuple[dict, dict]:
        """Contrôle la règle résultante.

        ``attrs`` : champs fournis ; ``current`` : valeurs actuelles de la
        règle (vide à la création). Retourne ``(attrs normalisés, erreurs)``.
        """
        attrs = dict(attrs)

        def value(field, default=None):
            return attrs[field] if field in attrs else current.get(field, default)

        operator = value("operator")
        low = value("threshold")
        high = value("threshold_high")
        hysteresis = value("hysteresis", 0) or 0
        definition = MetricCatalog.get(value("metric"))
        errors = {}

        if definition and operator and operator not in definition.operators:
            errors["operator"] = "Cet opérateur n'est pas disponible pour ce type de mesure."

        if operator in Operator.RANGE:
            if high is None:
                errors["threshold_high"] = "La borne haute est obligatoire pour un intervalle."
            elif low is not None and high <= low:
                errors["threshold_high"] = "La borne haute doit être supérieure à la borne basse."
            elif low is not None and operator == Operator.OUTSIDE_RANGE and 2 * hysteresis >= high - low:
                errors["hysteresis"] = "L'hystérésis doit être inférieure à la moitié de l'intervalle."
        elif "threshold_high" in attrs and high is not None:
            errors["threshold_high"] = "Une seule valeur seuil est attendue pour cet opérateur."
        elif operator and "operator" in attrs:
            # Passage d'un intervalle à un seuil simple : la borne haute est effacée.
            attrs["threshold_high"] = None

        if hysteresis < 0:
            errors["hysteresis"] = "L'hystérésis doit être positive ou nulle."

        if definition:
            errors.update(self._bounds_errors(definition, low, high, hysteresis, errors))
        return attrs, errors

    @staticmethod
    def _bounds_errors(definition, low, high, hysteresis, existing):
        errors = {}
        bounds = definition.plausible_range
        for field, value in (("threshold", low), ("threshold_high", high)):
            if value is None or field in existing:
                continue
            if bounds and not bounds[0] <= value <= bounds[1]:
                errors[field] = (
                    f"Valeur hors des limites physiques du capteur ({bounds[0]} à {bounds[1]} {definition.unit})."
                )
            elif definition.integer and float(value) != int(value):
                errors[field] = "Ce paramètre est un comptage : utilisez un nombre entier."
        if definition.integer and float(hysteresis) != int(hysteresis) and "hysteresis" not in existing:
            errors["hysteresis"] = "Ce paramètre est un comptage : utilisez un nombre entier."
        return errors
