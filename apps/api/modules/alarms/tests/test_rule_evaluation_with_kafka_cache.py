from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from modules.alarms.domain.alarm_state_machine import AlarmStateMachine
from modules.alarms.domain.alert_message_builder import AlertMessageBuilder
from modules.alarms.domain.condition_evaluator import ConditionEvaluator
from modules.alarms.repositories.alarm_rule_repository import AlarmRuleRepository
from modules.alarms.repositories.rule_state_repository import RuleStateRepository
from modules.alarms.services.rule_evaluation_service import RuleEvaluationService
from modules.alarms.stores.rule_state_store import RuleStateStore
from modules.database.models import AlarmRule, Zone
from shared.caching.local_cache import LocalCache


class RecordingProducer:
    """Producteur factice : rien n'est persisté, comme si le module Database
    n'avait pas encore traité les événements publiés."""

    def __init__(self):
        self.raised, self.resolved, self.states = [], [], []

    def alert_raised(self, **event):
        self.raised.append(event)

    def alert_resolved(self, **event):
        self.resolved.append(event)

    def state_saved(self, **event):
        self.states.append(event)


class RuleEvaluationWithKafkaCacheTests(TestCase):
    """Avec Kafka, la base est mise à jour après coup : le moteur doit
    s'appuyer sur sa propre vue des états pour ne pas déclencher deux fois."""

    def setUp(self):
        self.zone = Zone.objects.create(name="Salle", code="salle")
        self.rule = AlarmRule.objects.create(name="Bruit", metric="sound_level", operator="gt", threshold=70)
        self.producer = RecordingProducer()
        self.t0 = timezone.now()

    def service(self, cache_enabled):
        return RuleEvaluationService(
            rules=AlarmRuleRepository(),
            states=RuleStateStore(RuleStateRepository(), LocalCache(enabled=cache_enabled)),
            producer=self.producer,
            evaluator=ConditionEvaluator(),
            machine=AlarmStateMachine(),
            messages=AlertMessageBuilder(),
        )

    def observation(self, value, minutes, identifier):
        return {
            "id": identifier,
            "zone_code": "salle",
            "zone_name": "Salle",
            "type": "sound_level",
            "value": value,
            "observed_at": (self.t0 + timedelta(minutes=minutes)).isoformat(),
            "received_at": self.t0.isoformat(),
            "quality_status": "normal",
        }

    def test_ongoing_alarm_is_not_triggered_twice(self):
        service = self.service(cache_enabled=True)
        events = service.evaluate(self.observation(80, 1, 1)) + service.evaluate(self.observation(85, 2, 2))
        self.assertEqual(events, [("triggered", self.rule.pk)])
        self.assertEqual(self.producer.raised[1]["refresh_fields"], ("observation",))

        service.evaluate(self.observation(60, 3, 3))
        self.assertEqual(len(self.producer.resolved), 1)
        self.assertEqual([state["state"].status for state in self.producer.states], ["active", "active", "normal"])
