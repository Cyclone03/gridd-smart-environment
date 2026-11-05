from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from modules.database.models import Alert, Zone


class AlertEventsApiTests(TestCase):
    def setUp(self):
        self.zone = Zone.objects.create(name="Salle", code="salle")
        self.old = Alert.objects.create(
            zone=self.zone,
            code="X",
            message="ancienne",
            severity="warning",
            active=False,
            created_at=timezone.now() - timedelta(days=3),
            resolved_at=timezone.now(),
        )
        self.current = Alert.objects.create(zone=self.zone, code="Y", message="en cours", severity="critical")

    def ids(self, query):
        return [item["id"] for item in self.client.get(f"/api/alerts/{query}").json()]

    def test_filters(self):
        self.assertEqual(self.ids("?active=true"), [self.current.id])
        self.assertEqual(self.ids("?severity=warning"), [self.old.id])
        since = (timezone.now() - timedelta(days=1)).isoformat()
        response = self.client.get("/api/alerts/", {"since": since})
        self.assertEqual([item["id"] for item in response.json()], [self.current.id])
        self.assertEqual(self.ids("?limit=1"), [self.current.id])

    def test_invalid_filter_is_rejected(self):
        response = self.client.get("/api/alerts/?since=hier")
        self.assertEqual(response.status_code, 400)
        self.assertIn("since", response.json()["errors"])

    def test_detail(self):
        self.assertEqual(self.client.get(f"/api/alerts/{self.current.id}/").json()["message"], "en cours")
        self.assertEqual(self.client.get("/api/alerts/999/").status_code, 404)
