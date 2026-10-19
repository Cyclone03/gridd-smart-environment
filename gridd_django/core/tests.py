from unittest.mock import patch
import json
from datetime import datetime, timedelta, timezone as datetime_timezone

from confluent_kafka import OFFSET_END
from django.test import Client, TestCase
from django.utils import timezone
from .management.commands.consume_kafka import assign_partitions_at_live_edge
from .kafka import TOPIC_TO_TYPE, process_message
from .models import Alert, Zone, ThresholdProfile, Sensor, Observation
from .services import ingest_observation


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
            "core.services.get_channel_layer",
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


class DashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_react_dashboard_is_the_homepage(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="root"')
        self.assertContains(response, "dashboard/dashboard.js")

    def test_react_dashboard_routes_survive_a_browser_refresh(self):
        for path in ["/spaces/", "/history/", "/alerts/"]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'id="root"')

    def test_legacy_dashboard_remains_available(self):
        response = self.client.get("/legacy/")

        self.assertEqual(response.status_code, 200)


class HistoryApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.zone = Zone.objects.create(name="Bureau", code="bureau", zone_type="office")
        self.sensor = Sensor.objects.create(
            node_id="bureau-temperature",
            sensor_type="temperature",
            zone=self.zone,
            unit="°C",
        )

    def test_history_returns_aggregates_for_requested_period(self):
        now = timezone.now()
        for offset, value in enumerate([21.0, 22.0, 23.0]):
            Observation.objects.create(
                sensor=self.sensor,
                zone=self.zone,
                type="temperature",
                value=value,
                unit="°C",
                observed_at=now - timedelta(minutes=30 - offset * 15),
            )

        response = self.client.get(
            "/api/zones/bureau/history/?type=temperature&hours=24"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["hours"], 24)
        self.assertEqual(payload["statistics"]["minimum"], 21.0)
        self.assertEqual(payload["statistics"]["maximum"], 23.0)
        self.assertEqual(payload["statistics"]["average"], 22.0)
        self.assertEqual(payload["statistics"]["count"], 3)

    def test_history_can_target_one_exact_local_calendar_day(self):
        local_timezone = timezone.get_current_timezone()
        selected_day = timezone.localdate()
        day_start = timezone.make_aware(
            datetime.combine(selected_day, datetime.min.time()),
            local_timezone,
        )
        Observation.objects.create(
            sensor=self.sensor,
            zone=self.zone,
            type="temperature",
            value=22.0,
            unit="°C",
            observed_at=day_start + timedelta(hours=10),
        )
        Observation.objects.create(
            sensor=self.sensor,
            zone=self.zone,
            type="temperature",
            value=99.0,
            unit="°C",
            observed_at=day_start - timedelta(minutes=1),
        )

        response = self.client.get(
            f"/api/zones/bureau/history/?type=temperature&date={selected_day.isoformat()}"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["date"], selected_day.isoformat())
        self.assertEqual(payload["statistics"]["count"], 1)
        self.assertEqual(payload["statistics"]["average"], 22.0)


class LatestObservationsApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.office = Zone.objects.create(
            name="Bureau des professeurs",
            code="professors-office",
            zone_type="office",
        )
        self.room = Zone.objects.create(
            name="Salle de réunion",
            code="meeting-room",
            zone_type="meeting_room",
        )
        self.temperature_sensor = Sensor.objects.create(
            node_id="office-temperature",
            sensor_type="temperature",
            zone=self.office,
            unit="°C",
        )
        self.humidity_sensor = Sensor.objects.create(
            node_id="room-humidity",
            sensor_type="humidity",
            zone=self.room,
            unit="%",
        )
        self.sound_sensor = Sensor.objects.create(
            node_id="office-sound",
            sensor_type="sound_level",
            zone=self.office,
            unit="dBA",
        )

    def test_latest_keeps_infrequent_metrics_outside_global_feed_limit(self):
        old_time = timezone.now() - timedelta(hours=1)
        temperature = Observation.objects.create(
            sensor=self.temperature_sensor,
            zone=self.office,
            type="temperature",
            value=22.4,
            unit="°C",
            observed_at=old_time,
        )
        humidity = Observation.objects.create(
            sensor=self.humidity_sensor,
            zone=self.room,
            type="humidity",
            value=41.0,
            unit="%",
            observed_at=None,
            received_at=old_time,
        )
        Observation.objects.bulk_create([
            Observation(
                sensor=self.sound_sensor,
                zone=self.office,
                type="sound_level",
                value=45.0,
                unit="dBA",
                observed_at=timezone.now() + timedelta(seconds=index),
            )
            for index in range(1001)
        ])

        feed_ids = {item["id"] for item in self.client.get("/api/observations/").json()}
        self.assertNotIn(temperature.id, feed_ids)
        self.assertNotIn(humidity.id, feed_ids)

        response = self.client.get("/api/observations/latest/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        latest_by_key = {(item["zone"], item["type"]): item for item in payload}
        self.assertEqual(
            latest_by_key[(self.office.id, "temperature")]["value"],
            22.4,
        )
        self.assertEqual(
            latest_by_key[(self.room.id, "humidity")]["value"],
            41.0,
        )


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
