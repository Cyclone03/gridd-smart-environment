from shared.kernel.events import MessageRejected
from shared.kernel.metrics import MetricCatalog


class ReadingValidator:
    """Vérifie la cohérence d'une mesure avec son type et avec le capteur de
    sa zone (activation, unité).

    Lève ``MessageRejected`` si la mesure doit être écartée ; retourne la
    valeur numérique sinon.
    """

    def validate(self, reading, zone_code, known_sensor) -> float:
        definition = MetricCatalog.get(reading.metric)
        if definition is None:
            raise MessageRejected(f"type de mesure inconnu: {reading.metric}")
        if definition.accepted_units and reading.unit not in definition.accepted_units:
            raise MessageRejected(f"unité incohérente pour {reading.metric}: {reading.unit}")

        if known_sensor is not None:
            label = f"{zone_code}/{reading.metric}"
            if not known_sensor.active:
                raise MessageRejected(f"capteur désactivé: {label}")
            if not self._same_unit(definition, known_sensor.unit, reading.unit):
                raise MessageRejected(f"unité incohérente pour {label}: base={known_sensor.unit}, kafka={reading.unit}")

        try:
            return float(reading.value)
        except (TypeError, ValueError) as exc:
            raise MessageRejected(f"valeur invalide: {reading.value}") from exc

    @staticmethod
    def _same_unit(definition, known, received) -> bool:
        """« °C » et « C » désignent la même unité (voir ``MetricCatalog``)."""
        if known == received:
            return True
        accepted = definition.accepted_units
        return bool(accepted) and known in accepted and received in accepted
