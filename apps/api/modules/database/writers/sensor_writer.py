from modules.database.models import Sensor


class SensorWriter:
    """Création des capteurs à leur première mesure et mise à jour de leurs métadonnées."""

    def upsert(self, *, node_id, metric, unit, zone, metadata) -> Sensor:
        sensor, created = Sensor.objects.get_or_create(
            node_id=node_id,
            sensor_type=metric,
            defaults={
                "label": f"{node_id} - {metric}",
                "zone": zone,
                "unit": unit,
                "metadata": metadata,
                "active": True,
            },
        )
        if not created and sensor.metadata != metadata:
            sensor.metadata = metadata
            sensor.save(update_fields=["metadata"])
        return sensor
