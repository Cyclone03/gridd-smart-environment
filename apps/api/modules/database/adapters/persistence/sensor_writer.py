import logging

from modules.database.models import Sensor

logger = logging.getLogger(__name__)


class SensorWriter:
    """Création des capteurs à leur première mesure et mise à jour de leurs métadonnées.

    Les champs horodatés des métadonnées (propres à chaque message) sont
    ignorés : sans cela, le capteur était réécrit à chaque mesure.

    Adaptateur du port ``SensorStore``.
    """

    VOLATILE_KEYS = frozenset({"observed_at", "observedAt", "timestamp", "received_at", "_kafka"})

    def upsert(self, *, node_id, metric, unit, zone, metadata) -> tuple[Sensor, bool]:
        """Retourne ``(capteur, changed)`` : ``changed`` est vrai si le capteur
        vient d'être créé ou a changé de zone (la liste des zones doit alors
        être republiée)."""
        sensor, created = Sensor.objects.get_or_create(
            node_id=node_id,
            sensor_type=metric,
            defaults={
                "label": f"{node_id} - {metric}",
                "zone": zone,
                "unit": unit,
                "metadata": self._stable(metadata),
                "active": True,
            },
        )
        if created:
            return sensor, True
        changed_fields = []
        stable = self._stable(metadata)
        if self._stable(sensor.metadata) != stable:
            sensor.metadata = stable
            changed_fields.append("metadata")
        moved = sensor.zone_id != zone.pk
        if moved:
            # Le message capteur fait foi : capteur déplacé ou réétiqueté.
            logger.warning(
                "Capteur %s/%s rattaché à la zone %s (auparavant zone id=%s).",
                node_id, metric, zone.code, sensor.zone_id,
            )
            sensor.zone = zone
            changed_fields.append("zone")
        if changed_fields:
            sensor.save(update_fields=changed_fields)
        return sensor, moved

    @classmethod
    def stable_metadata(cls, metadata):
        """Métadonnées sans les champs propres à chaque message."""
        return cls._stable(metadata)

    @classmethod
    def _stable(cls, metadata):
        if not isinstance(metadata, dict):
            return metadata
        return {key: value for key, value in metadata.items() if key not in cls.VOLATILE_KEYS}
