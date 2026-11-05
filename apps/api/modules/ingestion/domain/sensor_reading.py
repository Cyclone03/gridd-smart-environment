from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SensorReading:
    """Mesure telle que reçue d'un capteur, avant validation."""

    event_id: str
    node_id: str
    metric: str
    value: object
    unit: str
    observed_at: datetime | None
    received_at: datetime
    # Métadonnées envoyées par le capteur (zone, source…).
    source_metadata: dict
    # Métadonnées enregistrées avec l'observation : celles du capteur plus
    # l'origine Kafka (topic, partition, offset) et la source de l'horodatage.
    metadata: dict
