from datetime import timedelta
from uuid import uuid4

from django.test import Client, TestCase
from django.utils import timezone

from modules.database.models import ClimatePrediction, Observation, Sensor, WeatherSnapshot, Zone


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

    def test_latest_climate_predictions_returns_latest_per_active_zone_in_event_contract(self):
        now = timezone.now()
        inactive_zone = Zone.objects.create(
            name="Zone inactive",
            code="inactive-zone",
            zone_type="office",
            active=False,
        )
        old_prediction = ClimatePrediction.objects.create(
            event_id=uuid4(),
            zone=self.office,
            generated_at=now - timedelta(hours=2),
            target_at=now - timedelta(hours=1),
            predicted_temperature_c=21.5,
            predicted_humidity_percent=40.0,
            model_version="zone-model-v1",
            prediction_mode=ClimatePrediction.PredictionMode.EXPERIMENTAL,
        )
        latest_prediction = ClimatePrediction.objects.create(
            event_id=uuid4(),
            zone=self.office,
            generated_at=now - timedelta(minutes=5),
            target_at=now + timedelta(minutes=55),
            predicted_temperature_c=22.5,
            predicted_humidity_percent=42.0,
            model_version="zone-model-v2",
            prediction_mode=ClimatePrediction.PredictionMode.OPERATIONAL,
        )
        ClimatePrediction.objects.create(
            event_id=uuid4(),
            zone=self.room,
            generated_at=now - timedelta(minutes=10),
            target_at=now + timedelta(minutes=50),
            predicted_temperature_c=23.0,
            predicted_humidity_percent=43.0,
            model_version="meeting-model-v1",
            prediction_mode=ClimatePrediction.PredictionMode.EXPERIMENTAL,
        )
        ClimatePrediction.objects.create(
            event_id=uuid4(),
            zone=inactive_zone,
            generated_at=now,
            target_at=now + timedelta(hours=1),
            predicted_temperature_c=20.0,
            predicted_humidity_percent=45.0,
            model_version="inactive-model",
            prediction_mode=ClimatePrediction.PredictionMode.EXPERIMENTAL,
        )

        response = self.client.get("/api/climate-predictions/latest/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual({item["zone_code"] for item in payload}, {"professors-office", "meeting-room"})
        self.assertEqual(len(payload), 2)
        office_prediction = next(item for item in payload if item["zone_code"] == self.office.code)
        self.assertEqual(office_prediction["prediction_id"], latest_prediction.pk)
        self.assertNotEqual(office_prediction["prediction_id"], old_prediction.pk)
        self.assertEqual(
            set(office_prediction),
            {
                "prediction_id",
                "prediction_event_id",
                "zone_code",
                "generated_at",
                "target_at",
                "predicted_temperature_c",
                "predicted_humidity_percent",
                "model_version",
                "prediction_mode",
            },
        )
        self.assertEqual(office_prediction["prediction_event_id"], str(latest_prediction.event_id))
        self.assertEqual(office_prediction["prediction_mode"], ClimatePrediction.PredictionMode.OPERATIONAL)

    def test_latest_weather_snapshot_returns_the_newest_snapshot_or_null(self):
        now = timezone.now()
        WeatherSnapshot.objects.create(
            event_id=uuid4(),
            generated_at=now - timedelta(minutes=5),
            provider="open-meteo",
            current_at=now - timedelta(minutes=6),
            current_temperature_c=18.0,
            current_relative_humidity_percent=50.0,
            forecast_h1_at=now + timedelta(minutes=54),
            forecast_h1_temperature_c=19.0,
            forecast_h1_relative_humidity_percent=52.0,
        )
        latest = WeatherSnapshot.objects.create(
            event_id=uuid4(),
            generated_at=now,
            provider="open-meteo",
            current_at=now,
            current_temperature_c=20.0,
            current_relative_humidity_percent=60.0,
            forecast_h1_at=now + timedelta(hours=1),
            forecast_h1_temperature_c=21.0,
            forecast_h1_relative_humidity_percent=62.0,
        )

        response = self.client.get("/api/weather/latest/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["weather_snapshot_id"], latest.pk)
        self.assertEqual(payload["weather_snapshot_event_id"], str(latest.event_id))
        self.assertEqual(payload["provider"], "open-meteo")

    def test_latest_weather_snapshot_returns_null_when_no_snapshot_exists(self):
        response = self.client.get("/api/weather/latest/")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json())


class ZoneApiTests(TestCase):
    def test_zone_exposes_metrics_from_active_sensors(self):
        zone = Zone.objects.create(name="Salle", code="salle", zone_type="meeting_room")
        Sensor.objects.create(node_id="n1", sensor_type="humidity", zone=zone, unit="%")
        Sensor.objects.create(node_id="n1", sensor_type="temperature", zone=zone, unit="C")
        Sensor.objects.create(node_id="n2", sensor_type="sound_level", zone=zone, unit="dBA", active=False)

        payload = self.client.get("/api/zones/").json()

        self.assertEqual(payload[0]["metrics"], ["temperature", "humidity"])
        self.assertEqual(self.client.get(f"/api/zones/{zone.id}/").json()["code"], "salle")
