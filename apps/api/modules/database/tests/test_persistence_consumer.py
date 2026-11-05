import uuid

from django.test import TestCase
from django.utils import timezone

from modules.database.consumers.persistence_consumer import PersistenceConsumer
from modules.database.models import AlarmRule, Alert, Observation, Zone
from shared.contracts.event_types import EventTypes
from shared.contracts.topics import Topics
from shared.messaging import Event, InboundMessage


class RecordingPublisher:
    is_synchronous = True

    def __init__(self):
        self.published = []

    def publish(self, topic, event, key=None):
        self.published.append((topic, event))


class PersistenceConsumerTests(TestCase):
    """Le module Database applique les événements et commandes qu'il reçoit,
    de façon idempotente, et répond toujours aux commandes."""

    def setUp(self):
        self.publisher = RecordingPublisher()
        self.consumer = PersistenceConsumer.build(publisher=self.publisher)

    def deliver(self, event, topic=None):
        self.consumer.handle(InboundMessage(topic=topic or Topics.ingestion_observations(), value=event.encode()))

    def published(self, event_type):
        return [event for _, event in self.publisher.published if event.type == event_type]

    def observation_event(self, event_id):
        now = timezone.now().isoformat()
        payload = {
            "event_id": event_id,
            "node_id": "n1",
            "metric": "temperature",
            "value": 21.5,
            "unit": "°C",
            "observed_at": now,
            "received_at": now,
            "metadata": {"source": "test"},
            "sensor_metadata": {"source": "test"},
            "quality_status": "normal",
            "quality_reason": "",
            "zone": {"code": "salle", "name": "Salle", "type": None},
        }
        return Event(type=EventTypes.OBSERVATION_VALIDATED, payload=payload, source="ingestion")

    def test_redelivered_observation_is_persisted_once(self):
        event = self.observation_event(str(uuid.uuid4()))
        self.deliver(event)
        self.deliver(event)
        self.assertEqual(Observation.objects.count(), 1)
        self.assertEqual(Zone.objects.get(code="salle").zone_type, Zone.ZoneType.OTHER)
        persisted = self.published(EventTypes.OBSERVATION_PERSISTED)
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0].payload["zone_code"], "salle")

    def test_alert_raised_twice_keeps_a_single_active_alert(self):
        Zone.objects.create(name="Salle", code="salle")
        payload = {
            "zone_code": "salle",
            "code": "DATA_QUALITY_TEMPERATURE",
            "rule_id": None,
            "severity": "warning",
            "message": "Donnée suspecte",
            "trigger_value": 30,
            "observation_id": None,
            "refresh_fields": ["message", "severity"],
        }
        for _ in range(2):
            self.deliver(Event(type=EventTypes.ALERT_RAISED, payload=payload, source="alarms"))
        self.assertEqual(Alert.objects.filter(active=True).count(), 1)
        self.assertEqual(len(self.published(EventTypes.ALERTS_CHANGED)), 1)

    def command(self, command_type, payload):
        return Event(
            type=command_type,
            payload=payload,
            source="test",
            correlation_id="c-1",
            reply_to=Topics.database_replies(),
        )

    def test_command_success_and_failure_are_answered(self):
        fields = {"name": "R", "metric": "temperature", "operator": "gt", "threshold": 25, "zone": None}
        self.deliver(self.command(EventTypes.ALARM_RULE_CREATE, {"fields": fields}))
        rule = AlarmRule.objects.get()
        succeeded = self.published(EventTypes.COMMAND_SUCCEEDED)
        self.assertEqual(succeeded[0].payload, {"data": {"rule_id": rule.pk}})
        self.assertEqual(succeeded[0].correlation_id, "c-1")
        changed = self.published(EventTypes.ALARM_RULE_CHANGED)
        self.assertEqual(changed[0].payload["action"], "created")

        self.deliver(self.command(EventTypes.ALARM_RULE_DELETE, {"rule_id": 999}))
        failed = self.published(EventTypes.COMMAND_FAILED)
        self.assertEqual(failed[0].payload["error"]["code"], "not_found")

        self.deliver(self.command(EventTypes.ALARM_RULE_UPDATE, {"rule_id": rule.pk, "fields": {"zone": "inconnue"}}))
        errors = self.published(EventTypes.COMMAND_FAILED)[1].payload["error"]["errors"]
        self.assertEqual(errors, {"zone": ["Zone inconnue ou inactive."]})
