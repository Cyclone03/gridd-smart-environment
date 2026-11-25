import logging

from modules.ia.core.domain.publication_receipt import PublicationReceipt
from modules.ia.core.errors import PredictionPublicationError
from shared.contracts.topics import Topics
from shared.messaging import MessagingUnavailable

logger = logging.getLogger(__name__)


class EventBusPredictionPublisher:
    """Adaptateur du port ``PredictionPublisher`` : publie sur le bus
    d'événements partagé du backend (Kafka en production, mémoire en test),
    topic ``KAFKA_TOPIC_AI_PREDICTIONS``, consommé par le module Database.

    Hors lot, ``EventPublisher.publish`` attend l'accusé du broker : une
    absence d'accusé lève ``PredictionPublicationError``.
    """

    def __init__(self, publisher, topic=None):
        self._publisher = publisher
        self._topic = topic

    def publish_prediction(self, event) -> PublicationReceipt:
        receipt = self._publish(event, key=event.zone_code, zone_code=event.zone_code)
        logger.info(
            "Climate prediction published: event_id=%s zone=%s target_at=%s topic=%s",
            receipt.event_id,
            receipt.zone_code,
            event.target_at,
            receipt.topic,
        )
        return receipt

    def publish_weather_snapshot(self, event) -> PublicationReceipt:
        receipt = self._publish(event, key="weather", zone_code=None)
        logger.info(
            "Weather snapshot published: event_id=%s current_at=%s forecast_h1_at=%s topic=%s",
            receipt.event_id,
            event.current_at,
            event.forecast_h1_at,
            receipt.topic,
        )
        return receipt

    def _publish(self, event, *, key, zone_code) -> PublicationReceipt:
        topic = self._topic or Topics.ai_prediction_events()
        try:
            self._publisher.publish(topic, event.to_event(), key=key)
        except MessagingUnavailable as exc:
            logger.error("Event bus publication failed for %s (topic=%s): %s", event.event_id, topic, exc)
            raise PredictionPublicationError(f"Publication failed for event {event.event_id} on {topic}: {exc}") from exc
        return PublicationReceipt(event_id=event.event_id, topic=topic, zone_code=zone_code)
