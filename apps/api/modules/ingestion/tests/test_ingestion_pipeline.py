from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from modules.database.models import Alert, Observation, Sensor, ThresholdProfile, Zone
from shared.messaging import MessageRejected
from tests.support.sensor_pipeline import SensorPipeline


class IngestionPipelineTests(TestCase):
    """Chaîne complète : topic capteur → ingestion → database → alarms / realtime."""

    def setUp(self):
        self.zone = Zone.objects.create(name="Salle de cours", code="salle-cours", zone_type="classroom")
        ThresholdProfile.objects.create(zone=self.zone)
        self.sensor = Sensor.objects.create(node_id="classroom-temp-1", sensor_type="temperature", zone=self.zone, unit="°C")
        self.pipeline = SensorPipeline()

    @property
    def metadata(self):
        return {"zone": {"id": self.zone.code, "label": self.zone.name}}

    def ingest(self, value, observed_at=None, unit="°C"):
        return self.pipeline.ingest(
            node_id=self.sensor.node_id,
            observation_type="temperature",
            value=value,
            unit=unit,
            observed_at=observed_at or timezone.now(),
            metadata=self.metadata,
        )

    def test_observation_is_bound_to_sensor_zone(self):
        observation = self.ingest(22.5)
        self.assertEqual(observation.zone, self.zone)
        self.assertEqual(observation.quality_status, Observation.QualityStatus.NORMAL)
        self.assertIsNotNone(observation.event_id)

    def test_unit_mismatch_is_rejected(self):
        with self.assertRaisesMessage(MessageRejected, "unité incohérente"):
            self.ingest(40, unit="%")
        self.assertFalse(Observation.objects.exists())

    def test_new_zone_and_sensor_are_created_by_the_database_module(self):
        observation = self.pipeline.ingest(
            node_id="meeting-sound",
            observation_type="sound_level",
            value=42,
            unit="dBA",
            observed_at=timezone.now(),
            metadata={"zone": {"id": "meeting-room", "label": "Salle de réunion"}},
        )
        zone = Zone.objects.get(code="meeting-room")
        self.assertEqual((zone.name, zone.zone_type), ("Salle de réunion", Zone.ZoneType.MEETING_ROOM))
        self.assertFalse(zone.threshold_profile.enabled)
        self.assertEqual(observation.sensor.node_id, "meeting-sound")
        self.assertNotIn("_kafka", observation.sensor.metadata)
        self.assertIn("_kafka", observation.metadata)

    def test_observation_is_broadcast_once_persisted(self):
        class ChannelLayer:
            def __init__(self):
                self.events = []

            async def group_send(self, group, event):
                self.events.append((group, event))

        channel_layer = ChannelLayer()
        with patch("modules.realtime.services.realtime_broadcaster.get_channel_layer", return_value=channel_layer):
            observation = self.ingest(22.5)

        created = [(group, event) for group, event in channel_layer.events if event["type"] == "observation.created"]
        self.assertEqual([group for group, _ in created], ["dashboard", "zone_salle-cours"])
        self.assertEqual(created[0][1]["payload"]["id"], observation.pk)
        # La température déclenche aussi une évaluation de confort, relayée à son tour.
        self.assertIn("comfort.updated", {event["type"] for _, event in channel_layer.events})

    def test_rapid_temperature_change_creates_and_resolves_quality_alert(self):
        started_at = timezone.now() - timedelta(minutes=1)
        self.ingest(19, started_at)
        suspicious = self.ingest(25, started_at + timedelta(seconds=30))

        self.assertEqual(suspicious.quality_status, Observation.QualityStatus.SUSPICIOUS)
        alert = Alert.objects.get(zone=self.zone, code="DATA_QUALITY_TEMPERATURE", active=True)
        self.assertEqual(alert.observation, suspicious)

        self.ingest(25.05, started_at + timedelta(minutes=2))
        self.assertFalse(Alert.objects.filter(zone=self.zone, code="DATA_QUALITY_TEMPERATURE", active=True).exists())

    def test_impossible_value_is_marked_invalid(self):
        observation = self.ingest(120)
        self.assertEqual(observation.quality_status, Observation.QualityStatus.INVALID)
        self.assertIn("limites physiques", observation.quality_reason)

    def test_unchanged_value_is_marked_suspicious_after_zone_delay(self):
        profile = self.zone.threshold_profile
        profile.stuck_after_minutes = 5
        profile.save(update_fields=["stuck_after_minutes"])
        started_at = timezone.now() - timedelta(minutes=10)
        self.ingest(22, started_at)
        observation = self.ingest(22, started_at + timedelta(minutes=6))

        self.assertEqual(observation.quality_status, Observation.QualityStatus.SUSPICIOUS)
        self.assertIn("valeur inchangée", observation.quality_reason)
