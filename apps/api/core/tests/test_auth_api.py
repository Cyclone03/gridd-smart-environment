from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from core.permissions import ALARM_MANAGERS_GROUP, ensure_alarm_managers_group


class AuthApiTests(TestCase):
    def setUp(self):
        cache.clear()
        ensure_alarm_managers_group()
        self.user = User.objects.create_user("gestion", password="motdepasse-solide", first_name="Gestion")
        self.user.groups.add(Group.objects.get(name=ALARM_MANAGERS_GROUP))
        self.client = APIClient()

    def login(self, password="motdepasse-solide"):
        return self.client.post("/api/auth/token/", {"username": "gestion", "password": password}, format="json")

    def test_login_me_logout(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["user"]["username"], "gestion")
        self.assertEqual(body["user"]["permissions"]["alarm_rules"], {"add": True, "change": True, "delete": True})
        self.assertIn("expires_at", body)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {body['token']}")
        self.assertEqual(self.client.get("/api/auth/me/").json()["display_name"], "Gestion")
        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 204)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_bad_credentials(self):
        response = self.login("mauvais")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Identifiant ou mot de passe incorrect."})
        self.assertEqual(self.client.post("/api/auth/token/", {}, format="json").status_code, 400)

    def test_new_login_rotates_token(self):
        first = self.login().json()["token"]
        second = self.login().json()["token"]
        self.assertNotEqual(first, second)
        self.assertFalse(Token.objects.filter(key=first).exists())

    @override_settings(AUTH_TOKEN_TTL_HOURS=1)
    def test_expired_token_is_rejected(self):
        token = self.login().json()["token"]
        Token.objects.filter(key=token).update(created=Token.objects.get(key=token).created - timedelta(hours=2))
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 401)
        self.assertIn("expirée", response.json()["detail"])

    def test_user_without_group_has_no_rule_permissions(self):
        User.objects.create_user("lecteur", password="motdepasse-solide")
        response = self.client.post(
            "/api/auth/token/", {"username": "lecteur", "password": "motdepasse-solide"}, format="json"
        )
        self.assertEqual(
            response.json()["user"]["permissions"]["alarm_rules"],
            {"add": False, "change": False, "delete": False},
        )
