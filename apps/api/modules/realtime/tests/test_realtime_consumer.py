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


class ObservationBatchingTests(SimpleTestCase):
    def payload(self, sensor, observed_at, zone="salle", metric="temperature"):
        return {"id": f"{sensor}-{observed_at}", "zone_code": zone, "sensor": sensor, "type": metric, "observed_at": observed_at}

    def test_backlog_is_reduced_to_the_latest_value_per_sensor(self):
        from datetime import datetime, timezone as tz

        now = datetime(2026, 11, 14, 20, 0, tzinfo=tz.utc)
        old = [self.payload(1, f"2026-11-14T10:00:{second:02d}+00:00") for second in range(50)]
        old += [self.payload(2, "2026-11-14T10:00:00+00:00")]
        fresh = [self.payload(1, "2026-11-14T19:59:30+00:00"), self.payload(1, "2026-11-14T19:59:35+00:00")]
        kept = RealtimeConsumer.coalesce(old + fresh, now=now)
        self.assertEqual(len(kept), 4)  # 1 ancienne par capteur + toutes les récentes
        self.assertIn("1-2026-11-14T10:00:49+00:00", [item["id"] for item in kept])

    def test_a_batch_gives_one_broadcast(self):
        class Broadcaster(RecordingBroadcaster):
            def observations_created(self, payloads):
                self.calls.append(("batch", len(payloads)))

        broadcaster = Broadcaster()
        consumer = RealtimeConsumer(broadcaster, StubSnapshots())
        consumer.begin_batch()
        for second in range(30):
            event = Event(type=EventTypes.OBSERVATION_PERSISTED, payload=self.payload(1, f"2026-11-01T10:00:{second:02d}+00:00"))
            consumer.handle(InboundMessage(topic="t", value=event.encode()))
        consumer.end_batch()
        self.assertEqual(broadcaster.calls, [("batch", 1)])
