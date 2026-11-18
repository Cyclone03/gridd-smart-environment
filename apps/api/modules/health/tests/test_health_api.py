from django.test import TestCase


class HealthApiTests(TestCase):
    def test_health_reports_database_and_event_bus(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["database"], "connected")
        self.assertEqual(body["event_bus"], "memory")

    def test_health_reports_stale_data(self):
        from datetime import timedelta

        from django.utils import timezone

        from modules.database.models import Observation, Sensor, Zone

        zone = Zone.objects.create(name="Salle", code="salle")
        sensor = Sensor.objects.create(node_id="n1", sensor_type="temperature", zone=zone, unit="°C")
        old = timezone.now() - timedelta(hours=4)
        observation = Observation.objects.create(
            sensor=sensor, zone=zone, type="temperature", value=20, unit="°C", observed_at=old
        )
        Observation.objects.filter(pk=observation.pk).update(received_at=old)

        body = self.client.get("/api/health/").json()
        self.assertEqual(body["status"], "degraded")
        self.assertTrue(body["data"]["stale"])
        self.assertGreater(body["data"]["age_seconds"], 3 * 3600)

    def test_health_reports_an_unreachable_redis(self):
        from django.test import override_settings

        with override_settings(REDIS_URL="redis://127.0.0.1:1/0"):
            body = self.client.get("/api/health/").json()
        self.assertEqual(body["redis"], "error")
        self.assertEqual(body["status"], "degraded")
