from datetime import timedelta

from django.test import Client, TestCase
from django.utils import timezone

from modules.database.models import Observation, Sensor, Zone


class LatestObservationsApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.office = Zone.objects.create(name="Bureau des professeurs", code="professors-office", zone_type="office")
        self.room = Zone.objects.create(name="Salle de réunion", code="meeting-room", zone_type="meeting_room")
        self.temperature_sensor = Sensor.objects.create(
            node_id="office-temperature", sensor_type="temperature", zone=self.office, unit="°C"
        )
        self.humidity_sensor = Sensor.objects.create(node_id="room-humidity", sensor_type="humidity", zone=self.room, unit="%")
        self.sound_sensor = Sensor.objects.create(node_id="office-sound", sensor_type="sound_level", zone=self.office, unit="dBA")

    def test_latest_keeps_infrequent_metrics_outside_global_feed_limit(self):
        old_time = timezone.now() - timedelta(hours=1)
        temperature = Observation.objects.create(
            sensor=self.temperature_sensor, zone=self.office, type="temperature", value=22.4, unit="°C", observed_at=old_time
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
        Observation.objects.bulk_create(
            [
                Observation(
                    sensor=self.sound_sensor,
                    zone=self.office,
                    type="sound_level",
                    value=45.0,
                    unit="dBA",
                    observed_at=timezone.now() + timedelta(seconds=index),
                )
                for index in range(1001)
            ]
        )

        feed_ids = {item["id"] for item in self.client.get("/api/observations/").json()}
        self.assertNotIn(temperature.id, feed_ids)
        self.assertNotIn(humidity.id, feed_ids)

        response = self.client.get("/api/observations/latest/")

        self.assertEqual(response.status_code, 200)
        latest_by_key = {(item["zone"], item["type"]): item for item in response.json()}
        self.assertEqual(latest_by_key[(self.office.id, "temperature")]["value"], 22.4)
        self.assertEqual(latest_by_key[(self.room.id, "humidity")]["value"], 41.0)

    def test_zone_latest(self):
        Observation.objects.create(
            sensor=self.temperature_sensor,
            zone=self.office,
            type="temperature",
            value=21.0,
            unit="°C",
            observed_at=timezone.now(),
        )
        payload = self.client.get("/api/zones/professors-office/latest/").json()
        self.assertEqual(payload["zone"]["code"], "professors-office")
        self.assertEqual(list(payload["latest"]), ["temperature"])
        self.assertEqual(self.client.get("/api/zones/inconnue/latest/").status_code, 404)

    def test_sensors_filter(self):
        payload = self.client.get("/api/sensors/?zone=meeting-room").json()
        self.assertEqual([item["node_id"] for item in payload], ["room-humidity"])
        self.assertEqual(payload[0]["zone_name"], "Salle de réunion")


class ZoneApiTests(TestCase):
    def test_zone_exposes_metrics_from_active_sensors(self):
        zone = Zone.objects.create(name="Salle", code="salle", zone_type="meeting_room")
        Sensor.objects.create(node_id="n1", sensor_type="humidity", zone=zone, unit="%")
        Sensor.objects.create(node_id="n1", sensor_type="temperature", zone=zone, unit="C")
        Sensor.objects.create(node_id="n2", sensor_type="sound_level", zone=zone, unit="dBA", active=False)

        payload = self.client.get("/api/zones/").json()

        self.assertEqual(payload[0]["metrics"], ["temperature", "humidity"])
        self.assertEqual(self.client.get(f"/api/zones/{zone.id}/").json()["code"], "salle")
