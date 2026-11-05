from django.test import SimpleTestCase

from modules.realtime.consumers.realtime_consumer import RealtimeConsumer
from shared.contracts.event_types import EventTypes
from shared.messaging import Event, InboundMessage


class RecordingBroadcaster:
    def __init__(self):
        self.calls = []

    def observation_created(self, payload):
        self.calls.append(("observation", payload["id"]))

    def alerts_changed(self):
        self.calls.append(("alerts",))


class RealtimeConsumerTests(SimpleTestCase):
    def test_relays_persisted_facts_and_ignores_the_rest(self):
        broadcaster = RecordingBroadcaster()
        consumer = RealtimeConsumer(broadcaster)
        for event in (
            Event(type=EventTypes.OBSERVATION_PERSISTED, payload={"id": 7, "zone_code": "salle"}),
            Event(type=EventTypes.ALARM_RULE_CHANGED, payload={"rule_id": 1}),
            Event(type=EventTypes.ALERTS_CHANGED, payload={"zone_code": "salle"}),
        ):
            consumer.handle(InboundMessage(topic="gridd.backend.database.events", value=event.encode()))
        self.assertEqual(broadcaster.calls, [("observation", 7), ("alerts",)])
