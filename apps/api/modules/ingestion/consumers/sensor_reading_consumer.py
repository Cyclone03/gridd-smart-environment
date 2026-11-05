import logging

from django.utils import timezone

from modules.ingestion.domain.quality_assessor import QualityAssessor
from modules.ingestion.domain.reading_validator import ReadingValidator
from modules.ingestion.domain.zone_resolver import ZoneResolver
from modules.ingestion.parsers.sensor_message_parser import SensorMessageParser
from modules.ingestion.producers.validated_observation_producer import ValidatedObservationProducer
from modules.ingestion.repositories.quality_profile_repository import QualityProfileRepository
from modules.ingestion.repositories.sensor_history_repository import SensorHistoryRepository
from modules.ingestion.repositories.sensor_repository import SensorRepository
from modules.ingestion.services.ingestion_service import IngestionService
from modules.ingestion.stores.sensor_history_store import SensorHistoryStore
from shared.caching.local_cache import LocalCache
from shared.contracts.topics import Topics
from shared.messaging import MessageHandler, MessageRejected, Messaging

logger = logging.getLogger(__name__)


class SensorReadingConsumer(MessageHandler):
    """Point d'entrée Kafka de l'ingestion : un message par mesure capteur."""

    def __init__(self, parser, service, clock=timezone.now):
        self._parser = parser
        self._service = service
        self._clock = clock

    @classmethod
    def build(cls):
        service = IngestionService(
            zone_resolver=ZoneResolver(),
            sensors=SensorRepository(),
            validator=ReadingValidator(),
            history=SensorHistoryStore(SensorHistoryRepository(), LocalCache.for_event_bus()),
            profiles=QualityProfileRepository(),
            assessor=QualityAssessor(),
            producer=ValidatedObservationProducer(Messaging.current().publisher()),
        )
        return cls(SensorMessageParser(Topics.sensors()), service)

    def handle(self, message):
        reading = self._parser.parse(message, received_at=self._clock())
        try:
            payload = self._service.ingest(reading)
        except MessageRejected as exc:
            zone = reading.source_metadata.get("zone") or {}
            raise MessageRejected(
                f"topic={message.topic} node_id={reading.node_id} zone={zone.get('id', 'unknown')} "
                f"type={reading.metric} value={reading.value} unit={reading.unit} error={exc}"
            ) from exc
        logger.info(
            "%s | %s | %s | %s %s | quality=%s",
            payload["zone"]["code"],
            payload["node_id"],
            payload["metric"],
            payload["value"],
            payload["unit"],
            payload["quality_status"],
        )
