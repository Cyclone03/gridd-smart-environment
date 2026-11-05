from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from shared.caching.local_cache import LocalCache
from shared.messaging.kafka_connection_config import KafkaConnectionConfig
from shared.messaging.subscription_registry import SubscriptionRegistry


class KafkaConnectionConfigTests(SimpleTestCase):
    def test_plaintext(self):
        config = KafkaConnectionConfig(bootstrap_servers="kafka:9092").client_config()
        self.assertEqual(config, {"bootstrap.servers": "kafka:9092", "security.protocol": "PLAINTEXT"})

    def test_sasl_ssl_requires_credentials_and_certificate(self):
        with self.assertRaises(ImproperlyConfigured):
            KafkaConnectionConfig(bootstrap_servers="k:9096", security_protocol="SASL_SSL").client_config()
        with self.assertRaisesMessage(ImproperlyConfigured, "introuvable"):
            KafkaConnectionConfig(
                bootstrap_servers="k:9096",
                security_protocol="SASL_SSL",
                username="u",
                password="p",
                ca_cert_path="/inexistant.crt",
            ).client_config()


class LocalCacheTests(SimpleTestCase):
    def test_enabled_cache_evicts_oldest_entries(self):
        cache = LocalCache(enabled=True, max_entries=2)
        for key in "abc":
            cache.put(key, key.upper())
        self.assertIsNone(cache.get("a"))
        self.assertEqual(cache.get("c"), "C")
        cache.discard_where(lambda key: key == "c")
        self.assertFalse(cache.contains("c"))

    def test_disabled_cache_never_returns_values(self):
        cache = LocalCache(enabled=False)
        cache.put("a", 1)
        self.assertIsNone(cache.get("a"))


class SubscriptionRegistryTests(SimpleTestCase):
    def test_each_consuming_module_declares_its_subscription(self):
        subscriptions = {item.name: item for item in SubscriptionRegistry().all()}
        self.assertEqual(set(subscriptions), {"database", "ingestion", "alarms", "comfort", "energy", "realtime"})
        self.assertTrue(subscriptions["ingestion"].start_at_live_edge)
        self.assertEqual(subscriptions["ingestion"].connection, "sensors")
        with self.assertRaises(ValueError):
            SubscriptionRegistry().select(["inconnu"])
