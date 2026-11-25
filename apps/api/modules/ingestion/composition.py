"""Racine de composition du module Ingestion."""

from django.conf import settings

from modules.ingestion.adapters.messaging.sensor_message_parser import SensorMessageParser
from modules.ingestion.adapters.messaging.sensor_reading_consumer import SensorReadingConsumer
from modules.ingestion.adapters.messaging.validated_observation_producer import ValidatedObservationProducer
from modules.ingestion.adapters.persistence.quality_profile_repository import QualityProfileRepository
from modules.ingestion.adapters.persistence.sensor_history_repository import SensorHistoryRepository
from modules.ingestion.adapters.persistence.sensor_history_store import SensorHistoryStore
from modules.ingestion.adapters.persistence.sensor_repository import SensorRepository
from modules.ingestion.core.domain.quality_assessor import QualityAssessor
from modules.ingestion.core.domain.reading_validator import ReadingValidator
from modules.ingestion.core.domain.zone_resolver import ZoneResolver
from modules.ingestion.core.services.ingestion_service import IngestionService
from shared.caching.local_cache import LocalCache
from shared.contracts.topics import Topics
from shared.messaging import Messaging


def ingestion_service() -> IngestionService:
    return IngestionService(
        zone_resolver=ZoneResolver(settings.GRIDD_NODE_ZONES),
        sensors=SensorRepository(),
        validator=ReadingValidator(),
        history=SensorHistoryStore(SensorHistoryRepository(), LocalCache.for_event_bus()),
        profiles=QualityProfileRepository(),
        assessor=QualityAssessor(),
        producer=ValidatedObservationProducer(Messaging.current().publisher()),
    )


def sensor_reading_consumer() -> SensorReadingConsumer:
    return SensorReadingConsumer(SensorMessageParser(Topics.sensors()), ingestion_service())
