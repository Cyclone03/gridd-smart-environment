from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from modules.database.models import Sensor, Zone


class SeedGriddTests(TestCase):
    def test_lab_zone_has_an_active_occupancy_sensor_that_stays_active(self):
        call_command("seed_gridd", stdout=StringIO())
        call_command("seed_gridd", stdout=StringIO())  # relancé à chaque démarrage

        lab = Zone.objects.get(code="gridd")
        self.assertEqual((lab.name, lab.zone_type), ("Laboratoire GRIDD", Zone.ZoneType.LAB))
        self.assertTrue(Sensor.objects.get(node_id="gridd-occupancy", sensor_type="occupancy").active)
        self.assertFalse(Sensor.objects.filter(zone=lab).exclude(sensor_type="occupancy").exists())
