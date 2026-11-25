from modules.database.models import Observation
from modules.ingestion.core.domain.past_reading import PastReading


class SensorHistoryRepository:
    """Dernières mesures enregistrées d'un capteur (lecture seule).

    Source en base de ``SensorHistoryStore`` (adaptateur du port ``SensorHistory``).
    """

    def recent(self, sensor, metric, limit) -> list[PastReading]:
        rows = (
            Observation.objects.filter(sensor__node_id=sensor, sensor__sensor_type=metric)
            .order_by("-observed_at", "-received_at")
            .values("value", "observed_at", "received_at")[:limit]
        )
        return [PastReading(row["value"], row["observed_at"], row["received_at"]) for row in rows]
