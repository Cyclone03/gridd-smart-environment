import itertools
import json

from modules.database.models import Observation
from modules.ingestion.consumers.sensor_reading_consumer import SensorReadingConsumer
from shared.contracts.topics import Topics
from shared.messaging import InboundMessage


class SensorPipeline:
    """Injecte une mesure comme le ferait un capteur et retourne l'observation enregistrée.

    Le message brut est remis au consommateur d'ingestion ; la suite de la
    chaîne (database → alarms, realtime) passe par le bus mémoire, exactement
    comme en production avec Kafka. Une mesure refusée lève ``MessageRejected``.
    """

    _offsets = itertools.count(1)

    def __init__(self):
        self._consumer = SensorReadingConsumer.build()

    def ingest(self, *, node_id, observation_type, value, unit, observed_at=None, metadata=None, broker_timestamp_ms=None):
        payload = {"node_id": node_id, "type": observation_type, "value": value, "unit": unit, "metadata": metadata or {}}
        if observed_at is not None:
            payload["timestamp"] = observed_at.isoformat()
        message = InboundMessage(
            topic=Topics.sensor_topic_for(observation_type),
            value=json.dumps(payload).encode("utf-8"),
            partition=0,
            offset=next(self._offsets),
            timestamp_ms=broker_timestamp_ms,
        )
        last_id = Observation.objects.order_by("-id").values_list("id", flat=True).first() or 0
        self._consumer.handle(message)
        observation = Observation.objects.filter(id__gt=last_id).order_by("-id").first()
        if observation is None:
            raise AssertionError("La mesure n'a pas été enregistrée par le module Database.")
        return observation
