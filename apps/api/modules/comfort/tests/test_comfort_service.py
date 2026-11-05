from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from modules.database.models import ComfortAssessment, ComfortProfile, Sensor, ThresholdProfile, Zone
from tests.support.sensor_pipeline import SensorPipeline


class ComfortServiceTests(TestCase):
    """Chaîne complète : mesure → ingestion → database → comfort → database, puis API."""

    def setUp(self):
        self.zone = Zone.objects.create(name="Bureau", code="bureau", zone_type="office")
        ThresholdProfile.objects.create(zone=self.zone, enabled=False)
        Sensor.objects.create(node_id="t1", sensor_type="temperature", zone=self.zone, unit="°C")
        Sensor.objects.create(node_id="h1", sensor_type="humidity", zone=self.zone, unit="%")
        self.pipeline = SensorPipeline()
        self.client = APIClient()
        self.t0 = timezone.now() - timedelta(minutes=20)

    def ingest(self, metric, value, minutes):
        node, unit = ("t1", "°C") if metric == "temperature" else ("h1", "%")
        return self.pipeline.ingest(
            node_id=node,
            observation_type=metric,
            value=value,
            unit=unit,
            observed_at=self.t0 + timedelta(minutes=minutes),
            metadata={"zone": {"id": "bureau", "label": "Bureau"}},
        )

    def test_each_temperature_or_humidity_reading_is_assessed_with_the_other_factor(self):
        self.ingest("temperature", 22, 0)
        self.ingest("humidity", 45, 1)
        observation = self.ingest("temperature", 25.5, 2)

        self.assertEqual(ComfortAssessment.objects.count(), 3)
        latest = ComfortAssessment.objects.get(observation=observation)
        self.assertEqual((latest.temperature, latest.humidity), (25.5, 45))
        self.assertEqual((latest.level, latest.temperature_status), ("acceptable", "warm"))
        first = ComfortAssessment.objects.order_by("assessed_at").first()
        self.assertEqual((first.humidity, first.humidity_status), (None, "unknown"))

    def test_invalid_reading_is_not_assessed(self):
        self.ingest("temperature", 120, 0)  # hors limites physiques
        self.assertFalse(ComfortAssessment.objects.exists())

    def test_current_and_history_endpoints(self):
        self.ingest("humidity", 45, 0)
        self.ingest("temperature", 17, 1)

        current = self.client.get("/api/comfort/current/").json()
        self.assertEqual(current[0]["zone_code"], "bureau")
        self.assertEqual(current[0]["assessment"]["level"], "uncomfortable")
        self.assertEqual(current[0]["profile"]["temperature_min"], 20)
        self.assertFalse(current[0]["customized"])

        history = self.client.get("/api/comfort/zones/bureau/history/", {"hours": 1}).json()
        self.assertEqual(history["summary"]["count"], 2)
        self.assertEqual(history["bucket_minutes"], 5)
        self.assertEqual(self.client.get("/api/comfort/zones/inconnue/history/").status_code, 404)
        self.assertEqual(self.client.get("/api/comfort/zones/bureau/history/", {"hours": 5}).status_code, 400)

    def test_profile_customization_changes_the_next_assessments(self):
        url = "/api/comfort/profiles/bureau/"
        response = self.client.patch(url, {"temperature_min": 16, "temperature_max": 19}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["customized"])
        self.assertEqual(ComfortProfile.objects.get(zone=self.zone).humidity_min, 30)  # valeur par défaut conservée

        self.ingest("temperature", 17, 0)
        self.assertEqual(ComfortAssessment.objects.get().level, "comfortable")

        reset = self.client.delete(url).json()
        self.assertFalse(reset["customized"])
        self.assertEqual(reset["profile"]["temperature_min"], 20)

    def test_profile_validation(self):
        url = "/api/comfort/profiles/bureau/"
        response = self.client.patch(url, {"temperature_min": 25}, format="json")  # > maximum par défaut (24)
        self.assertEqual(response.status_code, 400)
        self.assertIn("temperature_max", response.json()["errors"])
        self.assertIn("humidity_min", self.client.patch(url, {"humidity_min": -5}, format="json").json()["errors"])
        self.assertEqual(self.client.patch("/api/comfort/profiles/inconnue/", {}, format="json").status_code, 404)
        self.assertFalse(ComfortProfile.objects.exists())
