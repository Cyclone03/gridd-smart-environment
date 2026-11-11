from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from modules.database.models import AlarmRule
from shared.messaging import Messaging

BROKEN_SSL = {
    "bootstrap_servers": "kafka.invalid:9096",
    "security_protocol": "SASL_SSL",
    "sasl_mechanism": "SCRAM-SHA-256",
    "username": "u",
    "password": "p",
    "ca_cert_path": "./secrets/absent.crt",
}


@override_settings(EVENT_BUS="kafka", KAFKA_CONNECTIONS={"main": BROKEN_SSL, "sensors": BROKEN_SSL})
class ReadsDoNotNeedKafkaTests(TestCase):
    """Une lecture passe par la base : elle ne doit jamais créer de client Kafka."""

    def setUp(self):
        Messaging.reset()
        self.addCleanup(Messaging.reset)
        AlarmRule.objects.create(name="R", metric="humidity", operator="lt", threshold=20)

    def test_active_read_endpoints_work_without_kafka_configuration(self):
        client = APIClient()
        for url in ("/api/alarm-rules/",):
            with self.subTest(url=url):
                self.assertEqual(client.get(url).status_code, 200)

    def test_retired_feature_endpoints_are_not_routed(self):
        client = APIClient()
        for url in ("/api/comfort/profiles/", "/api/energy/profiles/"):
            with self.subTest(url=url):
                self.assertEqual(client.get(url).status_code, 404)
