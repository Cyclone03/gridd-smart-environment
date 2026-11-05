from django.test import TestCase


class HealthApiTests(TestCase):
    def test_health_reports_database_and_event_bus(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["database"], "connected")
        self.assertEqual(body["event_bus"], "memory")
