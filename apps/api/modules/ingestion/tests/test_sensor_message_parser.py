import json
from datetime import datetime
from datetime import timezone as datetime_timezone

from django.test import SimpleTestCase
from django.utils import timezone

from modules.ingestion.parsers.sensor_message_parser import SensorMessageParser
from shared.messaging import InboundMessage, MessageRejected

TOPIC = "gridd.obs.environmental.temperature"


class SensorMessageParserTests(SimpleTestCase):
    def setUp(self):
        self.parser = SensorMessageParser({TOPIC: "temperature"})
        self.received_at = timezone.now()

    def message(self, payload, topic=TOPIC, raw=None, **extra):
        value = raw if raw is not None else json.dumps(payload).encode("utf-8")
        return InboundMessage(topic=topic, value=value, **extra)

    def payload(self, **overrides):
        data = {
            "node_id": "environmental-node01",
            "type": "temperature",
            "value": 25.9,
            "unit": "C",
            "metadata": {"zone": {"id": "professors-office", "label": "Bureau des professeurs"}},
        }
        data.update(overrides)
        return data

    def test_broker_timestamp_is_used_when_payload_has_no_timestamp(self):
        timestamp_ms = 1792423137944
        reading = self.parser.parse(
            self.message(self.payload(), timestamp_ms=timestamp_ms, partition=2, offset=4812),
            self.received_at,
        )
        self.assertEqual(reading.observed_at, datetime.fromtimestamp(timestamp_ms / 1000, tz=datetime_timezone.utc))
        self.assertEqual(reading.metadata["timestamp_source"], "kafka_broker")
        self.assertEqual(
            reading.metadata["_kafka"],
            {"topic": TOPIC, "partition": 2, "offset": 4812, "timestamp_ms": timestamp_ms},
        )
        self.assertNotIn("_kafka", reading.source_metadata)

    def test_redelivered_message_keeps_the_same_event_id(self):
        first = self.parser.parse(self.message(self.payload(), partition=1, offset=7), self.received_at)
        again = self.parser.parse(self.message(self.payload(), partition=1, offset=7), self.received_at)
        other = self.parser.parse(self.message(self.payload(), partition=1, offset=8), self.received_at)
        self.assertEqual(first.event_id, again.event_id)
        self.assertNotEqual(first.event_id, other.event_id)

    def test_payload_timestamp_and_camel_case_fields(self):
        reading = self.parser.parse(
            self.message(self.payload(node_id=None, nodeId="n2", timestamp="2026-10-27T08:00:00-04:00")),
            self.received_at,
        )
        self.assertEqual(reading.node_id, "n2")
        self.assertEqual(reading.metadata["timestamp_source"], "payload")
        self.assertEqual(reading.observed_at.isoformat(), "2026-10-27T08:00:00-04:00")

    def test_invalid_messages_are_rejected(self):
        cases = [
            (self.message(None, raw=b"{pas du json"), "JSON"),
            (self.message(self.payload(), topic="autre.topic"), "topic inconnu"),
            (self.message(self.payload(type="humidity")), "type/topic incohérent"),
            (self.message(self.payload(node_id=None)), "node_id manquant"),
            (self.message({k: v for k, v in self.payload().items() if k != "value"}), "value manquante"),
            (self.message(self.payload(timestamp="hier")), "timestamp invalide"),
            (self.message(self.payload(metadata=[1])), "metadata"),
        ]
        for message, expected in cases:
            with self.subTest(expected=expected), self.assertRaisesMessage(MessageRejected, expected):
                self.parser.parse(message, self.received_at)
