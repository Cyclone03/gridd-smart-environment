import logging

from django.utils import timezone

from shared.messaging import MessageHandler, MessageRejected

logger = logging.getLogger(__name__)


class SensorReadingConsumer(MessageHandler):
    """Point d'entrée Kafka de l'ingestion : un message par mesure capteur.

    Assemblé par ``modules.ingestion.composition.sensor_reading_consumer``.
    """

    def __init__(self, parser, service, clock=timezone.now):
        self._parser = parser
        self._service = service
        self._clock = clock

    def handle(self, message):
        reading = self._parser.parse(message, received_at=self._clock())
        try:
            payload = self._service.ingest(reading)
        except MessageRejected as exc:
            zone = reading.source_metadata.get("zone")
            zone_id = zone.get("id", "unknown") if isinstance(zone, dict) else zone or "unknown"
            raise MessageRejected(
                f"topic={message.topic} node_id={reading.node_id} zone={zone_id} "
                f"type={reading.metric} value={reading.value} unit={reading.unit} error={exc}"
            ) from exc
        # Une ligne par mesure : niveau DEBUG (en INFO, des dizaines de lignes
        # par seconde ralentissaient le consommateur et noyaient les journaux).
        logger.debug(
            "%s | %s | %s | %s %s | quality=%s",
            payload["zone"]["code"],
            payload["node_id"],
            payload["metric"],
            payload["value"],
            payload["unit"],
            payload["quality_status"],
        )
