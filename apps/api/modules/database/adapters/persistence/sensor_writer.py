from modules.database.models import Sensor
from shared.kernel.metrics import MetricCatalog


class SensorWriter:
    """Capteurs : un par zone et par type de mesure (identifiant
    ``shared.kernel.sensor_identity.sensor_key``), créé à la première mesure.

    Les champs horodatés des métadonnées (propres à chaque message) sont
    ignorés : sans cela, le capteur était réécrit à chaque mesure.

    Adaptateur du port ``SensorStore``.
    """

    VOLATILE_KEYS = frozenset({"observed_at", "observedAt", "timestamp", "received_at", "_kafka"})

    def upsert(self, *, sensor, metric, unit, zone, metadata) -> tuple[Sensor, bool]:
        """Retourne ``(capteur, created)``."""
        stable = self._stable(metadata)
        record, created = Sensor.objects.get_or_create(
            node_id=sensor,
            sensor_type=metric,
            defaults={
                "label": self._label(zone, metric),
                "zone": zone,
                "unit": unit,
                "metadata": stable,
                "active": True,
            },
        )
        if not created and self._stable(record.metadata) != stable:
            record.metadata = stable
            record.save(update_fields=["metadata"])
        return record, created

    @classmethod
    def stable_metadata(cls, metadata):
        """Métadonnées sans les champs propres à chaque message."""
        return cls._stable(metadata)

    @classmethod
    def _stable(cls, metadata):
        if not isinstance(metadata, dict):
            return metadata
        return {key: value for key, value in metadata.items() if key not in cls.VOLATILE_KEYS}

    @staticmethod
    def _label(zone, metric):
        definition = MetricCatalog.get(metric)
        return f"{zone.name} — {definition.label if definition else metric}"
