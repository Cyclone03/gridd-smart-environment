from django.test import SimpleTestCase

from modules.realtime.consumers.realtime_consumer import RealtimeConsumer
from shared.contracts.event_types import EventTypes
from shared.messaging import Event, InboundMessage


class RecordingBroadcaster:
    def __init__(self):
        self.calls = []

    def observation_created(self, payload):
        self.calls.append(("observation", payload["id"]))

    def alerts_changed(self, payload):
        self.calls.append(("alerts", payload))

    def zones_changed(self, payload):
        self.calls.append(("zones", payload))


class StubSnapshots:
    def __init__(self, fail=False):
        self.fail = fail

    def alerts(self):
        if self.fail:
            raise RuntimeError("base indisponible")
        return {"active": [{"id": 1}], "history": []}

    def zones(self):
        return [{"code": "salle"}]


class RealtimeConsumerTests(SimpleTestCase):
    def deliver(self, consumer, *events):
        for event in events:
            consumer.handle(InboundMessage(topic="gridd.backend.database.events", value=event.encode()))

    def test_relays_persisted_facts_with_their_data_and_ignores_the_rest(self):
        broadcaster = RecordingBroadcaster()
        self.deliver(
            RealtimeConsumer(broadcaster, StubSnapshots()),
            Event(type=EventTypes.OBSERVATION_PERSISTED, payload={"id": 7, "zone_code": "salle"}),
            Event(type=EventTypes.ALARM_RULE_CHANGED, payload={"rule_id": 1}),
            Event(type=EventTypes.ALERTS_CHANGED, payload={"zone_code": "salle"}),
            Event(type=EventTypes.ZONES_CHANGED, payload={"zone_code": "salle"}),
        )
        self.assertEqual(
            broadcaster.calls,
            [
                ("observation", 7),
                ("alerts", {"active": [{"id": 1}], "history": []}),
                ("zones", [{"code": "salle"}]),
            ],
        )

    def test_database_failure_does_not_break_the_consumer(self):
        broadcaster = RecordingBroadcaster()
        with self.assertLogs("modules.realtime.consumers.realtime_consumer", level="ERROR"):
            self.deliver(
                RealtimeConsumer(broadcaster, StubSnapshots(fail=True)),
                Event(type=EventTypes.ALERTS_CHANGED, payload={"zone_code": "salle"}),
            )
        self.assertEqual(broadcaster.calls, [])


class RealtimeBatchingTests(SimpleTestCase):
    def test_a_burst_of_changes_is_broadcast_once_per_batch(self):
        broadcaster = RecordingBroadcaster()
        consumer = RealtimeConsumer(broadcaster, StubSnapshots())
        consumer.begin_batch()
        for _ in range(90):
            consumer.handle(
                InboundMessage(topic="t", value=Event(type=EventTypes.ALERTS_CHANGED, payload={}).encode())
            )
        consumer.handle(InboundMessage(topic="t", value=Event(type=EventTypes.ZONES_CHANGED, payload={}).encode()))
        self.assertEqual(broadcaster.calls, [])
        consumer.end_batch()
        self.assertEqual([kind for kind, _ in broadcaster.calls], ["alerts", "zones"])
