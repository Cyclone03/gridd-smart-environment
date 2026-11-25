"""Racine de composition du module Alarms."""

from modules.alarms.adapters.messaging.alarm_events_producer import AlarmEventsProducer
from modules.alarms.adapters.messaging.alarms_consumer import AlarmsConsumer
from modules.alarms.adapters.messaging.rule_command_gateway import RuleCommandGateway
from modules.alarms.adapters.persistence.alarm_rule_repository import AlarmRuleRepository
from modules.alarms.adapters.persistence.alert_repository import AlertRepository
from modules.alarms.adapters.persistence.quality_alert_store import QualityAlertStore
from modules.alarms.adapters.persistence.rule_state_repository import RuleStateRepository
from modules.alarms.adapters.persistence.rule_state_store import RuleStateStore
from modules.alarms.core.domain.alarm_state_machine import AlarmStateMachine
from modules.alarms.core.domain.alert_message_builder import AlertMessageBuilder
from modules.alarms.core.domain.condition_evaluator import ConditionEvaluator
from modules.alarms.core.domain.rule_change_policy import RuleChangePolicy
from modules.alarms.core.services.alarm_rule_catalog_service import AlarmRuleCatalogService
from modules.alarms.core.services.alarm_rule_service import AlarmRuleService
from modules.alarms.core.services.alert_query_service import AlertQueryService
from modules.alarms.core.services.quality_alert_service import QualityAlertService
from modules.alarms.core.services.rule_change_service import RuleChangeService
from modules.alarms.core.services.rule_evaluation_service import RuleEvaluationService
from shared.caching.local_cache import LocalCache
from shared.messaging import Messaging


def alarm_rule_service() -> AlarmRuleService:
    return AlarmRuleService(AlarmRuleRepository(), RuleCommandGateway(Messaging.current().gateway()))


def alarm_rule_catalog_service() -> AlarmRuleCatalogService:
    return AlarmRuleCatalogService()


def alert_query_service() -> AlertQueryService:
    return AlertQueryService(AlertRepository())


def rule_evaluation_service(*, states, producer, messages=None) -> RuleEvaluationService:
    return RuleEvaluationService(
        rules=AlarmRuleRepository(),
        states=states,
        producer=producer,
        evaluator=ConditionEvaluator(),
        machine=AlarmStateMachine(),
        messages=messages or AlertMessageBuilder(),
    )


def alarms_consumer() -> AlarmsConsumer:
    producer = AlarmEventsProducer(Messaging.current().publisher())
    messages = AlertMessageBuilder()
    states = RuleStateStore(RuleStateRepository(), LocalCache.for_event_bus())
    return AlarmsConsumer(
        quality_alerts=QualityAlertService(
            store=QualityAlertStore(AlertRepository(), LocalCache.for_event_bus()),
            producer=producer,
            messages=messages,
        ),
        rule_evaluation=rule_evaluation_service(states=states, producer=producer, messages=messages),
        rule_changes=RuleChangeService(states=states, producer=producer, policy=RuleChangePolicy()),
    )
