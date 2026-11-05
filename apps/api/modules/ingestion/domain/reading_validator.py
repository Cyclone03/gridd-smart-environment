from shared.messaging import MessageRejected
from shared.metrics.metric_catalog import MetricCatalog


class ReadingValidator:
    """Vérifie la cohérence d'une mesure avec son capteur et son type.

    Lève ``MessageRejected`` si la mesure doit être écartée ; retourne la
    valeur numérique sinon.
    """

    def validate(self, reading, zone_code, known_sensor) -> float:
        label = f"{reading.node_id}/{reading.metric}"
        if known_sensor is not None:
            if not known_sensor.active:
                raise MessageRejected(f"capteur désactivé: {reading.node_id}")
            if known_sensor.zone_code != zone_code:
                raise MessageRejected(f"zone incohérente pour {label}: base={known_sensor.zone_code}, kafka={zone_code}")
            if known_sensor.unit != reading.unit:
                raise MessageRejected(f"unité incohérente pour {label}: base={known_sensor.unit}, kafka={reading.unit}")

        definition = MetricCatalog.get(reading.metric)
        if definition is None:
            raise MessageRejected(f"type de mesure inconnu: {reading.metric}")
        if definition.accepted_units and reading.unit not in definition.accepted_units:
            raise MessageRejected(f"unité incohérente pour {reading.metric}: {reading.unit}")

        try:
            return float(reading.value)
        except (TypeError, ValueError) as exc:
            raise MessageRejected(f"valeur invalide: {reading.value}") from exc
