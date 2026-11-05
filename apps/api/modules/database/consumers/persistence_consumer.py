import logging

from modules.database.mappers.observation_payload_mapper import ObservationPayloadMapper
from modules.database.producers.command_reply_producer import CommandReplyProducer
from modules.database.producers.database_events_producer import DatabaseEventsProducer
from modules.database.services.alarm_rule_persistence_service import AlarmRulePersistenceService
from modules.database.services.alert_persistence_service import AlertPersistenceService
from modules.database.services.comfort_persistence_service import ComfortPersistenceService
from modules.database.services.energy_persistence_service import EnergyPersistenceService
from modules.database.services.observation_persistence_service import ObservationPersistenceService
from modules.database.writers.alarm_rule_state_writer import AlarmRuleStateWriter
from modules.database.writers.alarm_rule_writer import AlarmRuleWriter
from modules.database.writers.alert_writer import AlertWriter
from modules.database.writers.comfort_writer import ComfortWriter
from modules.database.writers.energy_writer import EnergyWriter
from modules.database.writers.observation_writer import ObservationWriter
from modules.database.writers.sensor_writer import SensorWriter
from modules.database.writers.zone_writer import ZoneWriter
from shared.contracts.event_types import EventTypes
from shared.messaging import CommandFailed, EventHandler, Messaging

logger = logging.getLogger(__name__)


class PersistenceConsumer(EventHandler):
    """Point d'entrée Kafka du module Database.

    Reçoit les événements des topics ``DATABASE_SUBSCRIBED_TOPICS`` et les
    transmet au service de persistance concerné. Les commandes (événements
    avec ``reply_to``) reçoivent toujours une réponse, succès ou échec.
    """

    def __init__(self, *, observations, alerts, rules, comfort, energy, replies):
        self._observations = observations
        self._alerts = alerts
        self._rules = rules
        self._comfort = comfort
        self._energy = energy
        self._replies = replies

    @classmethod
    def build(cls, publisher=None):
        publisher = publisher or Messaging.current().publisher()
        producer = DatabaseEventsProducer(publisher)
        zone_writer = ZoneWriter()
        return cls(
            observations=ObservationPersistenceService(
                zone_writer=zone_writer,
                sensor_writer=SensorWriter(),
                observation_writer=ObservationWriter(),
                mapper=ObservationPayloadMapper(),
                producer=producer,
            ),
            alerts=AlertPersistenceService(
                zone_writer=zone_writer,
                alert_writer=AlertWriter(),
                state_writer=AlarmRuleStateWriter(),
                producer=producer,
            ),
            rules=AlarmRulePersistenceService(rule_writer=AlarmRuleWriter(), producer=producer),
            comfort=ComfortPersistenceService(zone_writer=zone_writer, comfort_writer=ComfortWriter(), producer=producer),
            energy=EnergyPersistenceService(zone_writer=zone_writer, energy_writer=EnergyWriter(), producer=producer),
            replies=CommandReplyProducer(publisher),
        )

    def routes(self):
        return {
            EventTypes.OBSERVATION_VALIDATED: lambda event: self._observations.persist(event.payload),
            EventTypes.ALERT_RAISED: lambda event: self._alerts.raise_alert(event.payload),
            EventTypes.ALERT_RESOLVED: lambda event: self._alerts.resolve_alert(event.payload),
            EventTypes.ALARM_STATE_SAVED: lambda event: self._alerts.save_state(event.payload),
            EventTypes.ALARM_RULE_RESET: lambda event: self._alerts.reset_rule(event.payload),
            EventTypes.ALARM_RULE_SEVERITY_PROPAGATED: lambda event: self._alerts.propagate_severity(event.payload),
            EventTypes.ALARM_RULE_CREATE: lambda event: self._command(event, self._rules.create),
            EventTypes.ALARM_RULE_UPDATE: lambda event: self._command(event, self._rules.update),
            EventTypes.ALARM_RULE_DELETE: lambda event: self._command(event, self._rules.delete),
            EventTypes.COMFORT_ASSESSED: lambda event: self._comfort.record_assessment(event.payload),
            EventTypes.COMFORT_PROFILE_SAVE: lambda event: self._command(event, self._comfort.save_profile),
            EventTypes.COMFORT_PROFILE_RESET: lambda event: self._command(event, self._comfort.reset_profile),
            EventTypes.ENERGY_ESTIMATED: lambda event: self._energy.record_estimate(event.payload),
            EventTypes.ENERGY_PROFILE_SAVE: lambda event: self._command(event, self._energy.save_profile),
            EventTypes.ENERGY_PROFILE_RESET: lambda event: self._command(event, self._energy.reset_profile),
        }

    def _command(self, event, operation):
        try:
            data = operation(event.payload)
        except CommandFailed as exc:
            self._replies.failed(event, exc)
            return
        except Exception:
            logger.exception("Échec de la commande %s.", event.type)
            self._replies.failed(event, CommandFailed(CommandFailed.ERROR, "Erreur lors de l'enregistrement."))
            return
        self._replies.succeeded(event, data)
