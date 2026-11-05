from django.test import TestCase


class RoutingTests(TestCase):
    def test_backend_does_not_serve_the_interface(self):
        for path in ["/", "/spaces/", "/history/", "/alerts/", "/legacy/"]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_api_routes_are_assembled_from_modules(self):
        paths = [
            "/api/health/",
            "/api/zones/",
            "/api/sensors/",
            "/api/observations/latest/",
            "/api/alerts/",
            "/api/alarm-rules/",
            "/api/comfort/current/",
            "/api/comfort/profiles/",
            "/api/energy/summary/",
            "/api/energy/profiles/",
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_authentication_endpoints_are_removed(self):
        for path in ["/api/auth/token/", "/api/auth/me/", "/api/auth/logout/"]:
            with self.subTest(path=path):
                self.assertEqual(self.client.post(path).status_code, 404)
