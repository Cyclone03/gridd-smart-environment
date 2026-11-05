from django.test import TestCase

from modules.database.models import Observation, Sensor, ThresholdProfile, Zone
from modules.simulator.services.simulator_service import SimulatorService


class SimulatorTests(TestCase):
    def test_simulated_readings_follow_the_sensor_pipeline(self):
        zone = Zone.objects.create(name="Salle de réunion", code="meeting-room")
        ThresholdProfile.objects.create(zone=zone, enabled=False)
        Sensor.objects.create(node_id="meeting-room-temperature", sensor_type="temperature", zone=zone, unit="°C")
        Sensor.objects.create(node_id="meeting-room-occupancy", sensor_type="occupancy", zone=zone, unit="count")

        simulator = SimulatorService.build()
        self.assertEqual(simulator.start(), 2)
        simulator.tick()

        observations = Observation.objects.filter(zone=zone)
        self.assertEqual(observations.count(), 2)
        self.assertTrue(all(item.metadata["source"] == "simulator" for item in observations))
        self.assertTrue(all(item.metadata["timestamp_source"] == "payload" for item in observations))
