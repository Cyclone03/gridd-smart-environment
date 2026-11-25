from shared.kernel.events import MessageRejected
from shared.kernel.metrics import MetricCatalog


class ReadingValidator:
    """Vérifie la cohérence d'une mesure avec son capteur (activation, unité)
    et son type.

    Lève ``MessageRejected`` si la mesure doit être écartée ; retourne la
    valeur numérique sinon.
    """

    def validate(self, reading, zone_code, known_sensor) -> float:
        label = f"{reading.node_id}/{reading.metric}"
        if known_sensor is not None:
            if not known_sensor.active:
                raise MessageRejected(f"capteur désactivé: {reading.node_id}")
            # Une zone différente de celle enregistrée n'est pas une erreur : le
            # capteur a été déplacé ou réétiqueté côté GRIDD. Le message fait foi
            # et le module Database rattache le capteur à sa nouvelle zone.
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
