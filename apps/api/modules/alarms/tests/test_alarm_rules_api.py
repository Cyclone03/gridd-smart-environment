from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from modules.database.models import AlarmRule, Alert, Zone
from shared.messaging import CommandTimeout
from shared.messaging.command_gateway import CommandGateway


class AlarmRulesApiTests(TestCase):
    url = "/api/alarm-rules/"

    def setUp(self):
        self.zone = Zone.objects.create(name="Salle de réunion", code="meeting-room")
        # Pas d'authentification pour le moment : un seul client, sans jeton.
        self.anonymous = APIClient()
        self.client_manager = self.anonymous

    def payload(self, **overrides):
        data = {
            "name": "Température élevée",
            "description": "Climatisation à vérifier",
            "zone": "meeting-room",
            "metric": "temperature",
            "operator": "gt",
            "threshold": 28,
            "severity": "warning",
            "enabled": True,
            "min_duration_seconds": 300,
            "hysteresis": 0.5,
        }
        data.update(overrides)
        return data

    def test_read_is_public(self):
        AlarmRule.objects.create(name="R", metric="humidity", operator="lt", threshold=20)
        response = self.anonymous.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["unit"], "%")
        self.assertEqual(response.json()[0]["condition_label"], "< 20 %")
        self.assertEqual(self.anonymous.get(self.url + "metadata/").status_code, 200)

    def test_writes_are_open_without_authentication(self):
        response = self.anonymous.post(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertIsNone(response.json()["created_by"])

    def test_manager_full_lifecycle(self):
        response = self.client_manager.post(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, 201, response.content)
        rule = response.json()
        self.assertEqual(rule["zone"], "meeting-room")
        self.assertEqual(rule["zone_name"], "Salle de réunion")
        self.assertEqual(rule["unit"], "°C")
        self.assertIsNone(rule["threshold_high"])

        detail = f"{self.url}{rule['id']}/"
        self.assertEqual(self.anonymous.get(detail).json()["name"], "Température élevée")

        patched = self.client_manager.patch(
            detail, {"operator": "outside_range", "threshold": 18, "threshold_high": 27}, format="json"
        )
        self.assertEqual(patched.status_code, 200, patched.content)
        self.assertEqual(patched.json()["condition_label"], "hors de [18 ; 27] °C")

        disabled = self.client_manager.patch(detail, {"enabled": False}, format="json")
        self.assertFalse(disabled.json()["enabled"])

        back_to_single = self.client_manager.patch(detail, {"operator": "lt", "threshold": 16}, format="json")
        self.assertEqual(back_to_single.status_code, 200, back_to_single.content)
        self.assertIsNone(back_to_single.json()["threshold_high"])

        self.assertEqual(self.client_manager.delete(detail).status_code, 204)
        self.assertFalse(AlarmRule.objects.exists())

    def test_global_rule_and_filters(self):
        self.client_manager.post(self.url, self.payload(zone=None, name="Globale"), format="json")
        self.client_manager.post(self.url, self.payload(metric="humidity", operator="lt", threshold=25), format="json")
        names = lambda query: sorted(item["name"] for item in self.anonymous.get(self.url + query).json())  # noqa: E731
        self.assertEqual(names("?zone=all"), ["Globale"])
        self.assertEqual(names("?metric=temperature"), ["Globale"])
        self.assertEqual(len(names("?zone=meeting-room")), 2)

    def test_validation(self):
        cases = [
            (self.payload(name="  "), "name"),
            (self.payload(metric="pression"), "metric"),
            (self.payload(operator="eq"), "operator"),
            (self.payload(operator="outside_range"), "threshold_high"),
            (self.payload(operator="outside_range", threshold=30, threshold_high=20), "threshold_high"),
            (self.payload(operator="gt", threshold_high=40), "threshold_high"),
            (self.payload(threshold=500), "threshold"),
            (self.payload(hysteresis=-1), "hysteresis"),
            (self.payload(operator="outside_range", threshold=20, threshold_high=22, hysteresis=1), "hysteresis"),
            (self.payload(metric="occupancy", threshold=12.5), "threshold"),
            (self.payload(metric="occupancy", threshold=12, hysteresis=0.5), "hysteresis"),
            (self.payload(min_duration_seconds=-5), "min_duration_seconds"),
            (self.payload(zone="inconnue"), "zone"),
            (self.payload(severity="urgent"), "severity"),
        ]
        for data, field in cases:
            with self.subTest(field=field, data=data):
                response = self.client_manager.post(self.url, data, format="json")
                self.assertEqual(response.status_code, 400)
                body = response.json()
                self.assertEqual(body["detail"], "Certaines données sont invalides.")
                self.assertIn(field, body["errors"])
        self.assertFalse(AlarmRule.objects.exists())

    def test_disabling_and_deleting_close_active_alerts(self):
        rule = AlarmRule.objects.create(name="R", metric="temperature", operator="gt", threshold=25)
        alert = Alert.objects.create(zone=self.zone, rule=rule, code=rule.alert_code, message="m", severity="warning")
        listing = self.anonymous.get(self.url).json()
        self.assertEqual(listing[0]["active_alerts"], 1)

        response = self.client_manager.patch(f"{self.url}{rule.id}/", {"enabled": False}, format="json")
        self.assertEqual(response.json()["active_alerts"], 0)
        alert.refresh_from_db()
        self.assertEqual((alert.active, alert.resolution), (False, Alert.Resolution.RULE_DISABLED))

        other = Alert.objects.create(zone=self.zone, rule=rule, code=rule.alert_code, message="m", severity="warning")
        self.client_manager.delete(f"{self.url}{rule.id}/")
        other.refresh_from_db()
        self.assertEqual((other.active, other.resolution, other.rule), (False, Alert.Resolution.RULE_DELETED, None))

    def test_put_is_not_exposed(self):
        rule = AlarmRule.objects.create(name="R", metric="temperature", operator="gt", threshold=25)
        response = self.client_manager.put(f"{self.url}{rule.id}/", self.payload(), format="json")
        self.assertEqual(response.status_code, 405)

    def test_unknown_rule_is_404(self):
        self.assertEqual(self.anonymous.get(f"{self.url}999/").status_code, 404)
        self.assertEqual(self.client_manager.patch(f"{self.url}999/", {"enabled": False}, format="json").status_code, 404)

    def test_persistence_unavailable_returns_503(self):
        with (
            patch.object(CommandGateway, "send", side_effect=CommandTimeout("pas de réponse")),
            self.assertLogs("shared.http.api_exception_handler", level="WARNING") as logs,
        ):
            response = self.client_manager.post(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, 503)
        self.assertIn("detail", response.json())
        # La cause réelle n'est pas renvoyée au client mais doit figurer dans les journaux.
        self.assertIn("CommandTimeout : pas de réponse", logs.output[0])
