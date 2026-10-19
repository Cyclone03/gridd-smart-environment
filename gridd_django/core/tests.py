from unittest.mock import patch

from django.test import Client, TestCase
from django.utils import timezone
from .models import Zone, ThresholdProfile, Sensor, Observation
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


class DashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_react_dashboard_is_the_homepage(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="root"')
        self.assertContains(response, "dashboard/dashboard.js")

    def test_legacy_dashboard_remains_available(self):
        response = self.client.get("/legacy/")

        self.assertEqual(response.status_code, 200)
