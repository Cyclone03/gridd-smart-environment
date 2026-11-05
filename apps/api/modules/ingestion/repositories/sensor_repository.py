from modules.database.models import Sensor
from modules.ingestion.domain.known_sensor import KnownSensor


class SensorRepository:
    """Lecture des capteurs connus (lecture seule)."""

    def find(self, node_id, metric) -> KnownSensor | None:
        row = (
            Sensor.objects.filter(node_id=node_id, sensor_type=metric)
            .values("zone__code", "unit", "active")
            .first()
        )
        if row is None:
            return None
        return KnownSensor(zone_code=row["zone__code"], unit=row["unit"], active=row["active"])
