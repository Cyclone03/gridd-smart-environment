"""Racine de composition du module Database."""

from modules.database.adapters.messaging.command_reply_producer import CommandReplyProducer
from modules.database.adapters.messaging.database_events_producer import DatabaseEventsProducer
from modules.database.adapters.messaging.persistence_consumer import PersistenceConsumer
from modules.database.adapters.persistence.alarm_rule_state_writer import AlarmRuleStateWriter
from modules.database.adapters.persistence.alarm_rule_writer import AlarmRuleWriter
from modules.database.adapters.persistence.alert_writer import AlertWriter
from modules.database.adapters.persistence.climate_prediction_writer import ClimatePredictionWriter
from modules.database.adapters.persistence.django_unit_of_work import DjangoUnitOfWork
from modules.database.adapters.persistence.observation_payload_mapper import ObservationPayloadMapper
from modules.database.adapters.persistence.observation_writer import ObservationWriter
from modules.database.adapters.persistence.sensor_writer import SensorWriter
from modules.database.adapters.persistence.weather_snapshot_writer import WeatherSnapshotWriter
from modules.database.adapters.persistence.zone_writer import ZoneWriter
from modules.database.core.services.alarm_rule_persistence_service import AlarmRulePersistenceService
from modules.database.core.services.alert_persistence_service import AlertPersistenceService
from modules.database.core.services.climate_prediction_persistence_service import ClimatePredictionPersistenceService
from modules.database.core.services.observation_persistence_service import ObservationPersistenceService
from modules.database.core.services.weather_snapshot_persistence_service import WeatherSnapshotPersistenceService
from shared.caching.local_cache import LocalCache
from shared.messaging import Messaging


def persistence_consumer(publisher=None) -> PersistenceConsumer:
    publisher = publisher or Messaging.current().publisher()
    producer = DatabaseEventsProducer(publisher)
    unit_of_work = DjangoUnitOfWork()
    zone_writer = ZoneWriter()
    return PersistenceConsumer(
        observations=ObservationPersistenceService(
            unit_of_work=unit_of_work,
            zone_writer=zone_writer,
            sensor_writer=SensorWriter(),
            observation_writer=ObservationWriter(),
            mapper=ObservationPayloadMapper(),
            producer=producer,
            cache_references=LocalCache.for_event_bus().enabled,
        ),
        alerts=AlertPersistenceService(
            unit_of_work=unit_of_work,
            zone_writer=zone_writer,
            alert_writer=AlertWriter(),
            state_writer=AlarmRuleStateWriter(),
            producer=producer,
        ),
        predictions=ClimatePredictionPersistenceService(
            unit_of_work=unit_of_work,
            zone_writer=zone_writer,
            prediction_writer=ClimatePredictionWriter(),
            producer=producer,
        ),
        weather_snapshots=WeatherSnapshotPersistenceService(
            unit_of_work=unit_of_work,
            snapshot_writer=WeatherSnapshotWriter(),
            producer=producer,
        ),
        rules=AlarmRulePersistenceService(unit_of_work=unit_of_work, rule_writer=AlarmRuleWriter(), producer=producer),
        replies=CommandReplyProducer(publisher),
    )
