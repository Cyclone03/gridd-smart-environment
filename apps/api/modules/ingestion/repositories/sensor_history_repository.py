from modules.database.models import Observation
from modules.ingestion.domain.past_reading import PastReading


class SensorHistoryRepository:
    """Dernières mesures enregistrées d'un capteur (lecture seule)."""

    def recent(self, node_id, metric, limit) -> list[PastReading]:
        rows = (
            Observation.objects.filter(sensor__node_id=node_id, sensor__sensor_type=metric)
            .order_by("-observed_at", "-received_at")
            .values("value", "observed_at", "received_at")[:limit]
        )
        return [PastReading(row["value"], row["observed_at"], row["received_at"]) for row in rows]
