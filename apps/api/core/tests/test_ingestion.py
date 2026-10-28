from datetime import datetime, timedelta, timezone as datetime_timezone
import json
from unittest.mock import patch

from confluent_kafka import OFFSET_END
from django.test import TestCase
from django.utils import timezone

from core.kafka import TOPIC_TO_TYPE, process_message
from core.management.commands.consume_kafka import assign_partitions_at_live_edge
from core.models import Alert, Observation, Sensor, ThresholdProfile, Zone
from core.services import ingest_observation


class IngestionTests(TestCase):
    def setUp(self):
        self.zone = Zone.objects.create(name="Salle de cours", code="salle-cours", zone_type="classroom")
        ThresholdProfile.objects.create(zone=self.zone)
        self.sensor = Sensor.objects.create(
            node_id="classroom-temp-1",
            sensor_type="temperature",
            zone=self.zone,
            unit="°C",
        )

    @property
    def metadata(self):
        return {
            "zone": {
                "id": self.zone.code,
                "label": self.zone.name,
            }
        }

    def test_observation_is_bound_to_sensor_zone(self):
        obs = ingest_observation(
            node_id="classroom-temp-1",
            observation_type="temperature",
            value=22.5,
            unit="°C",
            observed_at=timezone.now(),
            metadata=self.metadata,
        )
        self.assertEqual(obs.zone, self.zone)
        self.assertEqual(obs.quality_status, Observation.QualityStatus.NORMAL)

    def test_unit_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            ingest_observation(
                node_id="classroom-temp-1",
                observation_type="temperature",
                value=40,
                unit="%",
                observed_at=timezone.now(),
                metadata=self.metadata,
            )

    def test_observation_is_broadcast_after_commit(self):
        class ChannelLayer:
            def __init__(self):
                self.events = []

            async def group_send(self, group, event):
                self.events.append((group, event))

        channel_layer = ChannelLayer()

        with patch(
            "core.realtime.get_channel_layer",
            return_value=channel_layer,
        ), self.captureOnCommitCallbacks(execute=True):
            observation = ingest_observation(
                node_id="classroom-temp-1",
                observation_type="temperature",
                value=22.5,
                unit="°C",
                observed_at=timezone.now(),
                metadata=self.metadata,
            )

        self.assertEqual(
            [group for group, _ in channel_layer.events],
            ["dashboard", "zone_salle-cours"],
        )
        self.assertEqual(
            channel_layer.events[0][1]["payload"]["id"],
            observation.pk,
        )

    def test_rapid_temperature_change_creates_and_resolves_quality_alert(self):
        started_at = timezone.now() - timedelta(minutes=1)
        ingest_observation(
            node_id=self.sensor.node_id,
            observation_type="temperature",
            value=19,
            unit="°C",
            observed_at=started_at,
            metadata=self.metadata,
        )
        suspicious = ingest_observation(
            node_id=self.sensor.node_id,
            observation_type="temperature",
            value=25,
            unit="°C",
            observed_at=started_at + timedelta(seconds=30),
            metadata=self.metadata,
        )

        self.assertEqual(suspicious.quality_status, Observation.QualityStatus.SUSPICIOUS)
        self.assertTrue(
            Alert.objects.filter(
                zone=self.zone,
                code="DATA_QUALITY_TEMPERATURE",
                active=True,
            ).exists()
        )

        ingest_observation(
            node_id=self.sensor.node_id,
            observation_type="temperature",
            value=25.05,
            unit="°C",
            observed_at=started_at + timedelta(minutes=2),
            metadata=self.metadata,
        )
        self.assertFalse(
            Alert.objects.filter(
                zone=self.zone,
                code="DATA_QUALITY_TEMPERATURE",
                active=True,
            ).exists()
        )

    def test_impossible_value_is_marked_invalid(self):
        observation = ingest_observation(
            node_id=self.sensor.node_id,
            observation_type="temperature",
            value=120,
            unit="°C",
            observed_at=timezone.now(),
            metadata=self.metadata,
        )
        self.assertEqual(observation.quality_status, Observation.QualityStatus.INVALID)
        self.assertIn("limites physiques", observation.quality_reason)

    def test_unchanged_value_is_marked_suspicious_after_zone_delay(self):
        profile = self.zone.threshold_profile
        profile.stuck_after_minutes = 5
        profile.save(update_fields=["stuck_after_minutes"])
        started_at = timezone.now() - timedelta(minutes=10)
        ingest_observation(
            node_id=self.sensor.node_id,
            observation_type="temperature",
            value=22,
            unit="°C",
            observed_at=started_at,
            metadata=self.metadata,
        )
        observation = ingest_observation(
            node_id=self.sensor.node_id,
            observation_type="temperature",
            value=22,
            unit="°C",
            observed_at=started_at + timedelta(minutes=6),
            metadata=self.metadata,
        )

        self.assertEqual(observation.quality_status, Observation.QualityStatus.SUSPICIOUS)
        self.assertIn("valeur inchangée", observation.quality_reason)


class KafkaConsumerAssignmentTests(TestCase):
    def test_live_assignment_ignores_committed_backlog(self):
        class Partition:
            offset = 123

        class Consumer:
            assigned = None

            def assign(self, partitions):
                self.assigned = partitions

        consumer = Consumer()
        partitions = [Partition(), Partition()]

        assign_partitions_at_live_edge(consumer, partitions)

        self.assertIs(consumer.assigned, partitions)
        self.assertTrue(all(partition.offset == OFFSET_END for partition in partitions))


class KafkaMessageTimestampTests(TestCase):
    def test_broker_timestamp_is_used_when_payload_has_no_timestamp(self):
        zone = Zone.objects.create(
            name="Bureau des professeurs",
            code="professors-office",
            zone_type="office",
        )
        Sensor.objects.create(
            node_id="environmental-node01",
            sensor_type="temperature",
            zone=zone,
            unit="C",
        )
        topic = next(
            name for name, metric_type in TOPIC_TO_TYPE.items()
            if metric_type == "temperature"
        )
        timestamp_ms = 1792423137944
        payload = {
            "node_id": "environmental-node01",
            "type": "temperature",
            "value": 25.9,
            "unit": "C",
            "metadata": {
                "zone": {
                    "id": "professors-office",
                    "label": "Bureau des professeurs",
                }
            },
        }

        observation = process_message(
            topic,
            json.dumps(payload).encode("utf-8"),
            kafka_timestamp_ms=timestamp_ms,
            kafka_partition=2,
            kafka_offset=4812,
        )

        self.assertEqual(
            observation.observed_at,
            datetime.fromtimestamp(
                timestamp_ms / 1000,
                tz=datetime_timezone.utc,
            ),
        )
        self.assertEqual(observation.metadata["timestamp_source"], "kafka_broker")
        self.assertEqual(
            observation.metadata["_kafka"],
            {
                "topic": topic,
                "partition": 2,
                "offset": 4812,
                "timestamp_ms": timestamp_ms,
            },
        )
