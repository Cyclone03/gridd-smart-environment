import json
import uuid
from datetime import datetime
from datetime import timezone as datetime_timezone

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from modules.ingestion.domain.sensor_reading import SensorReading
from shared.messaging import MessageRejected


class SensorMessageParser:
    """Transforme un message brut d'un topic capteur en ``SensorReading``.

    Format attendu (JSON) : ``node_id`` (ou ``nodeId``), ``value``, ``unit``,
    ``type`` facultatif mais cohérent avec le topic, horodatage facultatif
    (``timestamp``, ``observed_at`` ou ``observedAt``) et ``metadata`` (objet).
    Sans horodatage, celui du broker Kafka est utilisé.
    """

    def __init__(self, topic_metrics):
        self._topic_metrics = dict(topic_metrics)

    def parse(self, message, received_at) -> SensorReading:
        payload = self._decode(message.value)
        expected_metric = self._topic_metrics.get(message.topic)
        if expected_metric is None:
            raise MessageRejected(f"topic inconnu: {message.topic}")

        metric = payload.get("type", expected_metric)
        if metric != expected_metric:
            raise MessageRejected(f"type/topic incohérent: type={metric}, topic={message.topic}")

        node_id = payload.get("node_id") or payload.get("nodeId")
        if not node_id:
            raise MessageRejected(f"node_id manquant sur topic={message.topic}")
        for field in ("value", "unit"):
            if field not in payload:
                raise MessageRejected(f"{field} manquante: {node_id}")

        source_metadata = payload.get("metadata", {})
        if not isinstance(source_metadata, dict):
            raise MessageRejected("metadata doit être un objet JSON")

        observed_raw = payload.get("timestamp") or payload.get("observed_at") or payload.get("observedAt")
        observed_at = self._observed_at(observed_raw, message.timestamp_ms)
        metadata = dict(source_metadata)
        metadata["_kafka"] = {
            "topic": message.topic,
            "partition": message.partition,
            "offset": message.offset,
            "timestamp_ms": message.timestamp_ms,
        }
        metadata["timestamp_source"] = "payload" if observed_raw else "kafka_broker" if observed_at else "received_at"

        return SensorReading(
            event_id=self._event_id(message),
            node_id=node_id,
            metric=metric,
            value=payload["value"],
            unit=payload["unit"],
            observed_at=observed_at,
            received_at=received_at,
            source_metadata=dict(source_metadata),
            metadata=metadata,
        )

    @staticmethod
    def _decode(raw):
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (AttributeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MessageRejected("JSON Kafka invalide") from exc
        if not isinstance(payload, dict):
            raise MessageRejected("Le message capteur doit être un objet JSON")
        return payload

    @staticmethod
    def _observed_at(raw, broker_timestamp_ms):
        if raw:
            observed_at = parse_datetime(str(raw))
            if observed_at is None:
                raise MessageRejected(f"timestamp invalide: {raw}")
            return timezone.make_aware(observed_at) if timezone.is_naive(observed_at) else observed_at
        if broker_timestamp_ms is not None and broker_timestamp_ms >= 0:
            return datetime.fromtimestamp(broker_timestamp_ms / 1000, tz=datetime_timezone.utc)
        return None

    @staticmethod
    def _event_id(message):
        # Identifiant stable pour un message Kafka donné : une relivraison
        # produit le même identifiant et n'est pas enregistrée deux fois.
        if message.partition is not None and message.offset is not None:
            return str(uuid.uuid5(uuid.NAMESPACE_URL, f"kafka:{message.topic}:{message.partition}:{message.offset}"))
        return str(uuid.uuid4())
