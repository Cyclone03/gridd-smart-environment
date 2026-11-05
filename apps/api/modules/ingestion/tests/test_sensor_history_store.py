from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from modules.ingestion.domain.past_reading import PastReading
from modules.ingestion.stores.sensor_history_store import SensorHistoryStore
from shared.caching.local_cache import LocalCache


class FakeRepository:
    def __init__(self, readings):
        self.readings = readings
        self.calls = 0

    def recent(self, node_id, metric, limit):
        self.calls += 1
        return list(self.readings)


class SensorHistoryStoreTests(SimpleTestCase):
    def setUp(self):
        self.now = timezone.now()
        self.repository = FakeRepository([PastReading(20, self.now - timedelta(minutes=2), self.now)])

    def test_with_kafka_own_readings_are_seen_before_persistence(self):
        store = SensorHistoryStore(self.repository, LocalCache(enabled=True))
        store.recent("n1", "temperature")
        store.record("n1", "temperature", PastReading(21, self.now, self.now))
        self.assertEqual([item.value for item in store.recent("n1", "temperature")], [21, 20])
        self.assertEqual(self.repository.calls, 1)

    def test_with_memory_bus_the_database_is_the_source_of_truth(self):
        store = SensorHistoryStore(self.repository, LocalCache(enabled=False))
        store.recent("n1", "temperature")
        store.record("n1", "temperature", PastReading(21, self.now, self.now))
        self.assertEqual([item.value for item in store.recent("n1", "temperature")], [20])
        self.assertEqual(self.repository.calls, 2)
