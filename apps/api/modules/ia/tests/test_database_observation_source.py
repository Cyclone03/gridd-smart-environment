from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from modules.database.models import Observation, Sensor, Zone
from modules.ia.adapters.persistence.database_observation_source import DatabaseObservationSource
from modules.ia.core.errors import IncompleteObservationsError, UnknownZoneError


class DatabaseObservationSourceTests(TestCase):
    def setUp(self):
        self.zone = Zone.objects.create(name="Salle de réunion", code="meeting-room")
        Zone.objects.create(name="Inactive", code="professors-office", active=False)
        self.now = timezone.now()

    def record(self, metric, value, unit, minutes_ago, quality="normal"):
        sensor, _ = Sensor.objects.get_or_create(
            node_id=f"n-{metric}", sensor_type=metric, defaults={"zone": self.zone, "unit": unit}
        )
        moment = self.now - timedelta(minutes=minutes_ago)
        return Observation.objects.create(
            sensor=sensor, zone=self.zone, type=metric, value=value, unit=unit,
            observed_at=moment, quality_status=quality,
        )

    def test_returns_the_latest_temperature_and_humidity_of_each_zone(self):
        self.record("temperature", 20.0, "°C", 10)
        self.record("temperature", 21.5, "°C", 2)
        self.record("humidity", 44.0, "%", 3, quality="suspicious")

        zones = DatabaseObservationSource().fetch_latest(["meeting-room"])

        observations = zones["meeting-room"]
        self.assertEqual((observations.temperature.value, observations.temperature.unit), (21.5, "°C"))
        self.assertEqual(observations.humidity.quality_status, "suspicious")
        self.assertIsNotNone(observations.humidity.received_at)

    def test_unknown_inactive_or_incomplete_zones_are_explicit_errors(self):
        source = DatabaseObservationSource()
        with self.assertRaises(UnknownZoneError):
            source.fetch_latest(["professors-office"])
        self.record("temperature", 21.0, "°C", 1)
        with self.assertRaisesRegex(IncompleteObservationsError, "humidity"):
            source.fetch_latest(["meeting-room"])
