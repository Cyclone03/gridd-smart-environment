from modules.alarms.domain.alarm_state_machine import AlarmStateMachine
from modules.alarms.domain.alert_message_builder import AlertMessageBuilder
from modules.alarms.domain.condition_evaluator import ConditionEvaluator
from modules.alarms.domain.rule_change_policy import RuleChangePolicy
from modules.alarms.producers.alarm_events_producer import AlarmEventsProducer
from modules.alarms.repositories.alarm_rule_repository import AlarmRuleRepository
from modules.alarms.repositories.alert_repository import AlertRepository
from modules.alarms.repositories.rule_state_repository import RuleStateRepository
from modules.alarms.services.quality_alert_service import QualityAlertService
from modules.alarms.services.rule_change_service import RuleChangeService
from modules.alarms.services.rule_evaluation_service import RuleEvaluationService
from modules.alarms.stores.quality_alert_store import QualityAlertStore
from modules.alarms.stores.rule_state_store import RuleStateStore
from shared.caching.local_cache import LocalCache
from shared.contracts.event_types import EventTypes
from shared.messaging import EventHandler, Messaging


class AlarmsConsumer(EventHandler):
    """Point d'entrée Kafka du moteur d'alarmes.

    - ``observation.persisted`` : alertes de qualité, puis règles d'alarme ;
    - ``alarm_rule.changed`` : effets d'une modification de règle.
    """

    def __init__(self, *, quality_alerts, rule_evaluation, rule_changes):
        self._quality_alerts = quality_alerts
        self._rule_evaluation = rule_evaluation
        self._rule_changes = rule_changes

    @classmethod
    def build(cls):
        producer = AlarmEventsProducer(Messaging.current().publisher())
        messages = AlertMessageBuilder()
        states = RuleStateStore(RuleStateRepository(), LocalCache.for_event_bus())
        return cls(
            quality_alerts=QualityAlertService(
                store=QualityAlertStore(AlertRepository(), LocalCache.for_event_bus()),
                producer=producer,
                messages=messages,
            ),
            rule_evaluation=RuleEvaluationService(
                rules=AlarmRuleRepository(),
                states=states,
                producer=producer,
                evaluator=ConditionEvaluator(),
                machine=AlarmStateMachine(),
                messages=messages,
            ),
            rule_changes=RuleChangeService(states=states, producer=producer, policy=RuleChangePolicy()),
        )

    def routes(self):
        return {
            EventTypes.OBSERVATION_PERSISTED: self._on_observation,
            EventTypes.ALARM_RULE_CHANGED: lambda event: self._rule_changes.apply(event.payload),
        }

    def _on_observation(self, event):
        self._quality_alerts.process(event.payload)
        self._rule_evaluation.evaluate(event.payload)
