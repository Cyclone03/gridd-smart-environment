import json
import unittest
from datetime import datetime, timedelta, timezone

from ai_prediction_service.messaging.kafka_producer import (
    DEFAULT_PREDICTIONS_TOPIC,
    KafkaPredictionProducer,
    KafkaProducerConfig,
    PredictionPublicationError,
)
from ai_prediction_service.domain.weather import WeatherPoint, WeatherSnapshot


class FakeMessage:
    def topic(self):
        return DEFAULT_PREDICTIONS_TOPIC

    def partition(self):
        return 2

    def offset(self):
        return 17


class FakeProducer:
    def __init__(self, *, delivery_error=None, outstanding=0, queue_full=False):
        self.delivery_error = delivery_error
        self.outstanding = outstanding
        self.queue_full = queue_full
        self.calls = []
        self.callbacks = []
        self.flush_timeout = None
        self.poll_timeouts = []

    def produce(self, topic, *, value, key, on_delivery):
        self.calls.append({"topic": topic, "value": value, "key": key})
        if self.queue_full:
            raise BufferError("queue full")
        self.callbacks.append(on_delivery)

    def poll(self, timeout):
        self.poll_timeouts.append(timeout)
        return 0

    def flush(self, timeout):
        self.flush_timeout = timeout
        callbacks, self.callbacks = self.callbacks, []
        for callback in callbacks:
            callback(self.delivery_error, FakeMessage())
        return self.outstanding


class KafkaProducerConfigTests(unittest.TestCase):
    def test_requires_explicit_bootstrap_and_builds_idempotent_producer_config(self):
        with self.assertRaisesRegex(ValueError, "KAFKA_BOOTSTRAP_SERVERS"):
            KafkaProducerConfig.from_env({})

        config = KafkaProducerConfig.from_env(
            {
                "KAFKA_BOOTSTRAP_SERVERS": "localhost:9094",
                "KAFKA_PUBLISH_TIMEOUT_SECONDS": "3.5",
            }
        )

        self.assertEqual(config.topic, DEFAULT_PREDICTIONS_TOPIC)
        self.assertEqual(
            config.client_config(),
            {
                "bootstrap.servers": "localhost:9094",
                "client.id": "gridd-ai-prediction-service",
                "security.protocol": "PLAINTEXT",
                "acks": "all",
                "enable.idempotence": True,
            },
        )
        self.assertEqual(config.publish_timeout_seconds, 3.5)

    def test_requires_sasl_credentials_and_positive_timeout(self):
        with self.assertRaisesRegex(ValueError, "KAFKA_USERNAME and KAFKA_PASSWORD"):
            KafkaProducerConfig.from_env(
                {
                    "KAFKA_BOOTSTRAP_SERVERS": "broker:9096",
                    "KAFKA_SECURITY_PROTOCOL": "SASL_SSL",
                }
            )
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            KafkaProducerConfig.from_env(
                {
                    "KAFKA_BOOTSTRAP_SERVERS": "localhost:9094",
                    "KAFKA_PUBLISH_TIMEOUT_SECONDS": "0",
                }
            )


class KafkaPredictionProducerTests(unittest.TestCase):
    def setUp(self):
        self.config = KafkaProducerConfig(
            bootstrap_servers="localhost:9094",
            publish_timeout_seconds=4.0,
        )
        self.fake = FakeProducer()
        self.publisher = KafkaPredictionProducer(self.config, producer=self.fake)

    def publish(self, **overrides):
        values = {
            "zone_code": "open-workspace",
            "target_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "predicted_temperature_c": 23.5,
            "predicted_humidity_percent": 45.0,
            "model_version": "modelZone1:sha256:0123456789abcdef",
            "prediction_mode": "operational",
        }
        values.update(overrides)
        return self.publisher.publish_prediction(**values)

    def publish_weather(self):
        generated_at = datetime.now(timezone.utc)
        snapshot = WeatherSnapshot(
            current=WeatherPoint(generated_at - timedelta(minutes=5), 18.2, 62.0),
            forecast_h1=WeatherPoint(generated_at + timedelta(minutes=55), 17.0, 65.0),
        )
        return self.publisher.publish_weather_snapshot(snapshot, generated_at=generated_at)

    def test_publishes_utf8_event_keyed_by_zone_and_returns_broker_ack(self):
        with self.assertLogs("ai_prediction_service.messaging.kafka_producer", level="INFO"):
            receipt = self.publish()

        self.assertEqual(len(self.fake.calls), 1)
        message = self.fake.calls[0]
        self.assertEqual(message["topic"], DEFAULT_PREDICTIONS_TOPIC)
        self.assertEqual(message["key"], "open-workspace")
        self.assertEqual(self.fake.flush_timeout, 4.0)
        payload = json.loads(message["value"].decode("utf-8"))
        self.assertEqual(payload["type"], "climate_prediction.generated")
        self.assertEqual(payload["payload"]["prediction_mode"], "operational")
        self.assertEqual(payload["payload"]["zone_code"], "open-workspace")
        self.assertEqual(receipt.topic, DEFAULT_PREDICTIONS_TOPIC)
        self.assertEqual(receipt.zone_code, "open-workspace")
        self.assertEqual((receipt.partition, receipt.offset), (2, 17))
        self.assertEqual(receipt.event_id, payload["event_id"])

    def test_publishes_weather_snapshot_on_the_site_wide_key(self):
        with self.assertLogs("ai_prediction_service.messaging.kafka_producer", level="INFO"):
            receipt = self.publish_weather()

        message = self.fake.calls[0]
        self.assertEqual(message["topic"], DEFAULT_PREDICTIONS_TOPIC)
        self.assertEqual(message["key"], "weather")
        payload = json.loads(message["value"].decode("utf-8"))
        self.assertEqual(payload["type"], "weather_snapshot.generated")
        self.assertEqual(payload["payload"]["current_temperature_c"], 18.2)
        self.assertEqual(payload["payload"]["forecast_h1_temperature_c"], 17.0)
        self.assertIsNone(receipt.zone_code)
        self.assertEqual(receipt.event_id, payload["event_id"])

    def test_invalid_prediction_inputs_do_not_publish(self):
        invalid_inputs = (
            {"zone_code": "unknown-zone"},
            {"predicted_temperature_c": float("nan")},
            {"predicted_humidity_percent": float("inf")},
            {"prediction_mode": "unknown"},
            {"model_version": ""},
        )
        for invalid in invalid_inputs:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.publish(**invalid)
        self.assertEqual(self.fake.calls, [])

    def test_delivery_error_and_flush_timeout_are_reported(self):
        self.fake.delivery_error = "broker rejected message"
        with self.assertLogs("ai_prediction_service.messaging.kafka_producer", level="ERROR"):
            with self.assertRaisesRegex(PredictionPublicationError, "delivery failed"):
                self.publish()

        self.fake.delivery_error = None
        self.fake.outstanding = 1
        with self.assertLogs("ai_prediction_service.messaging.kafka_producer", level="ERROR"):
            with self.assertRaisesRegex(PredictionPublicationError, "timed out"):
                self.publish()

    def test_full_queue_is_polled_and_retried_once_then_reported(self):
        self.fake.queue_full = True
        with self.assertLogs("ai_prediction_service.messaging.kafka_producer", level="ERROR"):
            with self.assertRaisesRegex(PredictionPublicationError, "queue remained full"):
                self.publish()

        self.assertEqual(len(self.fake.calls), 2)
        self.assertEqual(len(self.fake.poll_timeouts), 1)
        self.assertIsNone(self.fake.flush_timeout)


if __name__ == "__main__":
    unittest.main()
