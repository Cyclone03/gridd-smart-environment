from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from modules.database.models import Alert, Observation, Sensor, ThresholdProfile, Zone


class MergeZoneCommandTests(TestCase):
    def setUp(self):
        self.target = Zone.objects.create(name="Cubicule 01", code="individual-work-cubicle-01")
        self.source = Zone.objects.create(name="node01", code="node01")
        ThresholdProfile.objects.create(zone=self.source)
        sensor = Sensor.objects.create(node_id="node01-sound_level", sensor_type="sound_level", zone=self.source, unit="dBA")
        Observation.objects.create(
            sensor=sensor, zone=self.source, type="sound_level", value=51.8, unit="dBA", observed_at=timezone.now()
        )
        Alert.objects.create(zone=self.source, code="RULE_1", message="bruit", severity="warning")

    def test_dry_run_changes_nothing(self):
        call_command("merge_zone", "node01", self.target.code, "--dry-run", stdout=StringIO())
        self.assertTrue(Zone.objects.filter(code="node01").exists())
        self.assertEqual(Observation.objects.get().zone, self.source)

    def test_measures_sensors_and_alerts_move_to_the_target_zone(self):
        call_command("merge_zone", "node01", self.target.code, stdout=StringIO())

        self.assertFalse(Zone.objects.filter(code="node01").exists())
        observation = Observation.objects.get()
        self.assertEqual(observation.zone, self.target)
        self.assertEqual(observation.sensor.node_id, "individual-work-cubicle-01-sound_level")
        self.assertEqual(observation.sensor.metadata["source_node_id"], "node01-sound_level")
        self.assertEqual(Alert.objects.get().zone, self.target)
