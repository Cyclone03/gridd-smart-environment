from unittest.mock import patch

from django.test import SimpleTestCase

from modules.realtime.adapters.messaging.realtime_consumer import RealtimeConsumer
from modules.realtime.adapters.websocket.realtime_broadcaster import RealtimeBroadcaster
from modules.realtime.core.domain.realtime_groups import RealtimeGroups
from modules.realtime.core.services.realtime_relay_service import RealtimeRelayService
from shared.kernel.events.event_types import EventTypes
from shared.messaging import Event, InboundMessage, MessageRejected


class RecordingBroadcaster:
    def __init__(self):
        self.calls = []

    def observation_created(self, payload):
        self.calls.append(("observation", payload["id"]))

    def climate_prediction_created(self, payload):
        self.calls.append(("prediction", payload))

    def weather_snapshot_created(self, payload):
        self.calls.append(("weather", payload))

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
    @staticmethod
    def prediction_payload(zone_code="open-workspace", prediction_mode="experimental"):
        return {
            "prediction_id": 17,
            "prediction_event_id": "4b9ab2a9-98a8-47d1-92d0-b794957ca4a7",
            "zone_code": zone_code,
            "generated_at": "2026-11-15T18:00:00+00:00",
            "target_at": "2026-11-15T19:00:00+00:00",
            "predicted_temperature_c": 23.5,
            "predicted_humidity_percent": 45.0,
            "model_version": "zone-1-test",
            "prediction_mode": prediction_mode,
        }

    @staticmethod
    def weather_payload():
        return {
            "weather_snapshot_id": 8,
            "weather_snapshot_event_id": "88b8053b-634b-4a43-92b0-c22bed310001",
            "generated_at": "2026-11-15T18:00:00+00:00",
            "provider": "open-meteo",
            "current_at": "2026-11-15T18:00:00+00:00",
            "current_temperature_c": 18.5,
            "current_relative_humidity_percent": 55.0,
            "forecast_h1_at": "2026-11-15T19:00:00+00:00",
            "forecast_h1_temperature_c": 19.0,
            "forecast_h1_relative_humidity_percent": 57.0,
        }

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
        with self.assertLogs("modules.realtime.core.services.realtime_relay_service", level="ERROR"):
            self.deliver(
                RealtimeConsumer(broadcaster, StubSnapshots(fail=True)),
                Event(type=EventTypes.ALERTS_CHANGED, payload={"zone_code": "salle"}),
            )
        self.assertEqual(broadcaster.calls, [])

    def test_persisted_prediction_is_validated_and_routed_with_all_fields(self):
        broadcaster = RecordingBroadcaster()
        payload = self.prediction_payload(prediction_mode="operational")
        self.deliver(
            RealtimeConsumer(broadcaster, StubSnapshots()),
            Event(
                type=EventTypes.CLIMATE_PREDICTION_PERSISTED,
                payload=payload,
                source="database",
            ),
        )
        self.assertEqual(broadcaster.calls, [("prediction", payload)])

    def test_persisted_weather_snapshot_is_validated_and_routed_with_all_fields(self):
        broadcaster = RecordingBroadcaster()
        payload = RealtimeConsumerTests.weather_payload()
        self.deliver(
            RealtimeConsumer(broadcaster, StubSnapshots()),
            Event(
                type=EventTypes.WEATHER_SNAPSHOT_PERSISTED,
                payload=payload,
                source="database",
            ),
        )
        self.assertEqual(broadcaster.calls, [("weather", payload)])

    def test_invalid_weather_snapshots_are_rejected_without_diffusion(self):
        invalid_payloads = [
            {**self.weather_payload(), "provider": "unknown"},
            {**self.weather_payload(), "forecast_h1_at": "2026-11-15T18:00:00+00:00"},
            {**self.weather_payload(), "current_relative_humidity_percent": 101},
            {key: value for key, value in self.weather_payload().items() if key != "generated_at"},
        ]
        broadcaster = RecordingBroadcaster()
        consumer = RealtimeConsumer(broadcaster, StubSnapshots())

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(MessageRejected):
                    self.deliver(
                        consumer,
                        Event(
                            type=EventTypes.WEATHER_SNAPSHOT_PERSISTED,
                            payload=payload,
                            source="database",
                        ),
                    )

        self.assertEqual(broadcaster.calls, [])

    def test_experimental_and_operational_predictions_remain_distinct(self):
        broadcaster = RecordingBroadcaster()
        consumer = RealtimeConsumer(broadcaster, StubSnapshots())
        self.deliver(
            consumer,
            Event(
                type=EventTypes.CLIMATE_PREDICTION_PERSISTED,
                payload=self.prediction_payload(prediction_mode="experimental"),
                source="database",
            ),
            Event(
                type=EventTypes.CLIMATE_PREDICTION_PERSISTED,
                payload=self.prediction_payload(
                    zone_code="meeting-room",
                    prediction_mode="operational",
                ),
                source="database",
            ),
        )
        self.assertEqual(
            [call[1]["prediction_mode"] for call in broadcaster.calls],
            ["experimental", "operational"],
        )
        self.assertEqual(
            [call[1]["zone_code"] for call in broadcaster.calls],
            ["open-workspace", "meeting-room"],
        )

    def test_all_six_gridd_zone_codes_are_accepted(self):
        zone_codes = (
            "open-workspace",
            "server-equipment-room",
            "professors-office",
            "individual-work-cubicle-01",
            "meeting-room",
            "individual-work-cubicle-02",
        )
        broadcaster = RecordingBroadcaster()
        consumer = RealtimeConsumer(broadcaster, StubSnapshots())

        for zone_code in zone_codes:
            with self.subTest(zone_code=zone_code):
                self.deliver(
                    consumer,
                    Event(
                        type=EventTypes.CLIMATE_PREDICTION_PERSISTED,
                        payload=self.prediction_payload(zone_code=zone_code),
                        source="database",
                    ),
                )

        self.assertEqual(
            [call[1]["zone_code"] for call in broadcaster.calls],
            list(zone_codes),
        )

    def test_invalid_predictions_are_rejected_without_diffusion(self):
        invalid_payloads = []
        invalid_payloads.append({**self.prediction_payload(), "zone_code": "other-zone"})
        invalid_payloads.append({**self.prediction_payload(), "prediction_mode": "preview"})
        invalid_payloads.append({**self.prediction_payload(), "target_at": "2026-11-15T17:00:00+00:00"})
        invalid_payloads.append({**self.prediction_payload(), "generated_at": "2026-11-15T18:00:00"})
        invalid_payloads.append({**self.prediction_payload(), "predicted_temperature_c": float("nan")})
        invalid_payloads.append({**self.prediction_payload(), "prediction_mode": []})
        invalid_payloads.append({key: value for key, value in self.prediction_payload().items() if key != "model_version"})
        broadcaster = RecordingBroadcaster()
        consumer = RealtimeConsumer(broadcaster, StubSnapshots())

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(MessageRejected):
                    self.deliver(
                        consumer,
                        Event(
                            type=EventTypes.CLIMATE_PREDICTION_PERSISTED,
                            payload=payload,
                            source="database",
                        ),
                    )

        with self.assertRaises(MessageRejected):
            self.deliver(
                consumer,
                Event(
                    type=EventTypes.CLIMATE_PREDICTION_PERSISTED,
                    payload=self.prediction_payload(),
                    source="untrusted",
                ),
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
        from datetime import datetime
        from datetime import timezone as tz

        now = datetime(2026, 11, 14, 20, 0, tzinfo=tz.utc)
        old = [self.payload(1, f"2026-11-14T10:00:{second:02d}+00:00") for second in range(50)]
        old += [self.payload(2, "2026-11-14T10:00:00+00:00")]
        fresh = [self.payload(1, "2026-11-14T19:59:30+00:00"), self.payload(1, "2026-11-14T19:59:35+00:00")]
        kept = RealtimeRelayService.coalesce(old + fresh, now=now)
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


class RealtimeBroadcasterTests(SimpleTestCase):
    def test_weather_snapshot_is_sent_only_to_dashboard(self):
        payload = RealtimeConsumerTests.weather_payload()
        with patch.object(RealtimeBroadcaster, "_send") as send:
            RealtimeBroadcaster().weather_snapshot_created(payload)
        send.assert_called_once_with(
            [RealtimeGroups.DASHBOARD],
            {"type": "weather_snapshot.created", "payload": payload},
        )

    def test_prediction_is_sent_only_to_dashboard_and_its_zone_group(self):
        payload = RealtimeConsumerTests.prediction_payload(zone_code="meeting-room")
        with patch.object(RealtimeBroadcaster, "_send") as send:
            RealtimeBroadcaster().climate_prediction_created(payload)
        send.assert_called_once_with(
            [RealtimeGroups.DASHBOARD, RealtimeGroups.zone("meeting-room")],
            {"type": "climate_prediction.created", "payload": payload},
        )

    def test_channel_layer_errors_are_reported_without_raising(self):
        class FailingChannelLayer:
            async def group_send(self, group, event):
                raise RuntimeError("isolated channel layer failure")

        with patch(
            "modules.realtime.adapters.websocket.realtime_broadcaster.get_channel_layer",
            return_value=FailingChannelLayer(),
        ):
            with self.assertLogs(
                "modules.realtime.adapters.websocket.realtime_broadcaster",
                level="ERROR",
            ):
                RealtimeBroadcaster().climate_prediction_created(
                    RealtimeConsumerTests.prediction_payload()
                )
