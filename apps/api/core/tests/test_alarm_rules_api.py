from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework.test import APIClient

from core.authentication import issue_token
from core.models import AlarmRule, Alert, Zone
from core.permissions import ALARM_MANAGERS_GROUP, ensure_alarm_managers_group


class AlarmRulesApiTests(TestCase):
    url = "/api/alarm-rules/"

    def setUp(self):
        ensure_alarm_managers_group()
        self.zone = Zone.objects.create(name="Salle de réunion", code="meeting-room")
        self.manager = User.objects.create_user("gestion", password="motdepasse-solide")
        self.manager.groups.add(Group.objects.get(name=ALARM_MANAGERS_GROUP))
        self.viewer = User.objects.create_user("lecteur", password="motdepasse-solide")
        self.anonymous = APIClient()
        self.client_manager = self.client_for(self.manager)
        self.client_viewer = self.client_for(self.viewer)

    def client_for(self, user):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {issue_token(user).key}")
        return client

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

    def test_write_requires_authentication_and_permission(self):
        self.assertEqual(self.anonymous.post(self.url, self.payload(), format="json").status_code, 401)
        self.assertEqual(self.client_viewer.post(self.url, self.payload(), format="json").status_code, 403)
        self.assertFalse(AlarmRule.objects.exists())

    def test_manager_full_lifecycle(self):
        response = self.client_manager.post(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, 201, response.content)
        rule = response.json()
        self.assertEqual(rule["zone"], "meeting-room")
        self.assertEqual(rule["zone_name"], "Salle de réunion")
        self.assertEqual(rule["unit"], "°C")
        self.assertEqual(rule["created_by"], "gestion")
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
        names = lambda query: sorted(item["name"] for item in self.anonymous.get(self.url + query).json())
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
