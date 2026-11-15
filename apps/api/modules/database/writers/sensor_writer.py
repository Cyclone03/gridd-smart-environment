from modules.database.models import Sensor


class SensorWriter:
    """Création des capteurs à leur première mesure et mise à jour de leurs métadonnées.

    Les champs horodatés des métadonnées (propres à chaque message) sont
    ignorés : sans cela, le capteur était réécrit à chaque mesure.
    """

    VOLATILE_KEYS = frozenset({"observed_at", "observedAt", "timestamp", "received_at", "_kafka"})

    def upsert(self, *, node_id, metric, unit, zone, metadata) -> tuple[Sensor, bool]:
        """Retourne ``(capteur, created)``."""
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
        stable = self._stable(metadata)
        if not created and self._stable(sensor.metadata) != stable:
            sensor.metadata = stable
            sensor.save(update_fields=["metadata"])
        return sensor, created

    @classmethod
    def stable_metadata(cls, metadata):
        """Métadonnées sans les champs propres à chaque message."""
        return cls._stable(metadata)

    @classmethod
    def _stable(cls, metadata):
        if not isinstance(metadata, dict):
            return metadata
        return {key: value for key, value in metadata.items() if key not in cls.VOLATILE_KEYS}
