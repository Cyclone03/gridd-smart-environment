import json
from types import SimpleNamespace

from django.test import TestCase
from django.utils import timezone

from modules.database.models import Observation, ThresholdProfile, Zone
from modules.ingestion.adapters.messaging.sensor_topic_replayer import SensorTopicReplayer
from modules.ingestion.composition import sensor_reading_consumer
from shared.contracts.topics import Topics
from shared.messaging import Messaging


class FakeMessage:
    def __init__(self, topic, partition, offset, timestamp_ms, payload):
        self._topic, self._partition, self._offset = topic, partition, offset
        self._timestamp_ms, self._value = timestamp_ms, json.dumps(payload).encode()

    def error(self):
        return None

    def topic(self):
        return self._topic

    def partition(self):
        return self._partition

    def offset(self):
        return self._offset

    def timestamp(self):
        return (1, self._timestamp_ms)

    def key(self):
        return None

    def value(self):
        return self._value


class FakeConsumer:
    """Un topic, une partition ; offsets 0…n-1, horodatage = 1000 × offset."""

    def __init__(self, topic, messages):
        self.topic, self.messages = topic, messages
        self.position = None
        self.paused = []

    def list_topics(self, topic, timeout):
        found = {self.topic: SimpleNamespace(error=None, partitions={0: None})}
        return SimpleNamespace(topics={topic: found[topic]} if topic in found else {})

    def offsets_for_times(self, partitions, timeout):
        result = []
        for tp in partitions:
            offset = next((m.offset() for m in self.messages if m.timestamp()[1] >= tp.offset), -1)
            result.append(SimpleNamespace(topic=tp.topic, partition=tp.partition, offset=offset))
        return result

    def get_watermark_offsets(self, tp, timeout, cached):
        return 0, len(self.messages)

    def assign(self, partitions):
        self.position = partitions[0].offset

    def consume(self, count, timeout):
        batch = self.messages[self.position : self.position + count]
        self.position += len(batch)
        return batch

    def pause(self, partitions):
        self.paused.extend(partitions)


class SensorTopicReplayerTests(TestCase):
    def setUp(self):
        Messaging.reset()
        self.zone = Zone.objects.create(name="Cubicule 01", code="individual-work-cubicle-01")
        ThresholdProfile.objects.create(zone=self.zone)
        self.topic = Topics.sensor_topic_for("temperature")
        base = timezone.now().replace(microsecond=0)
        self.messages = [
            FakeMessage(
                self.topic, 0, offset, 1000 * offset,
                {
                    "node_id": "environmental-node04",
                    "type": "temperature",
                    "value": 22 + offset / 10,
                    "unit": "C",
                    "timestamp": (base - timezone.timedelta(minutes=10 - offset)).isoformat(),
                    "metadata": {"zone": {"id": self.zone.code, "label": self.zone.name}},
                },
            )
            for offset in range(6)
        ]

    def replayer(self, consumer):
        return SensorTopicReplayer(consumer, sensor_reading_consumer(), Messaging.current().publisher(), batch_size=4)

    def test_replays_the_period_and_never_duplicates_measurements(self):
        consumer = FakeConsumer(self.topic, self.messages)
        replayer = self.replayer(consumer)
        plan = replayer.plan([self.topic], since_ms=2000)
        self.assertEqual(plan, {(self.topic, 0): (2, 6)})

        report = replayer.replay(plan, until_ms=4000)
        self.assertEqual((report.read, report.accepted, report.rejected), (3, 3, 0))
        self.assertEqual(Observation.objects.count(), 3)
        self.assertEqual(Observation.objects.first().sensor.node_id, "individual-work-cubicle-01-temperature")

        again = self.replayer(FakeConsumer(self.topic, self.messages))
        again.replay(again.plan([self.topic], since_ms=0))
        self.assertEqual(Observation.objects.count(), 6)  # 3 manquantes ajoutées, 3 déjà présentes ignorées

    def test_nothing_to_replay_after_the_last_message(self):
        replayer = self.replayer(FakeConsumer(self.topic, self.messages))
        self.assertEqual(replayer.plan([self.topic], since_ms=10_000), {})
