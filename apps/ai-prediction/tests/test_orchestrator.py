import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from ai_prediction_service.domain.observations import MetricObservation, ZoneObservations
from ai_prediction_service.domain.weather import WeatherPoint, WeatherSnapshot
from ai_prediction_service.errors import OpenMeteoError
from ai_prediction_service.messaging.kafka_producer import (
    KafkaDeliveryReceipt,
    PredictionPublicationError,
)
from ai_prediction_service.models.zones import ZONE_MODEL_MAPPING
from ai_prediction_service.services.data_collection import CollectionSnapshot, DataCollectionService
from ai_prediction_service.services.orchestrator import PredictionInputError, PredictionOrchestrator
from ai_prediction_service.services.prediction_ledger import SQLitePredictionLedger


class FakeRegistry:
    def zone_codes(self):
        return tuple(ZONE_MODEL_MAPPING.values())

    def for_zone(self, zone_code):
        number = next(number for number, code in ZONE_MODEL_MAPPING.items() if code == zone_code)
        return SimpleNamespace(
            zone_number=number,
            model=SimpleNamespace(sha256=f"{number:064x}"),
        )


class FakeCollection:
    build_model_features = staticmethod(DataCollectionService.build_model_features)

    def __init__(self, snapshots, errors=None):
        self.snapshots = snapshots
        self.errors = errors or {}
        self.calls = []

    def fetch_weather(self):
        return next(iter(self.snapshots.values())).weather

    def collect(self, zone_codes):
        return self.collect_with_weather(zone_codes, self.fetch_weather())

    def collect_with_weather(self, zone_codes, weather):
        self.calls.append(tuple(zone_codes))
        zone_code = zone_codes[0]
        if zone_code in self.errors:
            raise self.errors[zone_code]
        return replace(self.snapshots[zone_code], weather=weather)


class FakePredictor:
    def __init__(self, errors=None, outputs=None):
        self.errors = errors or {}
        self.outputs = outputs or {}
        self.calls = []

    def predict_one(self, zone_code, features):
        self.calls.append((zone_code, features))
        if zone_code in self.errors:
            raise self.errors[zone_code]
        return self.outputs.get(zone_code, (23.5, 46.0))


class FakeProducer:
    def __init__(self, errors=None):
        self.errors = errors or {}
        self.calls = []
        self.weather_calls = []

    def publish_weather_snapshot(self, snapshot, *, generated_at=None):
        self.weather_calls.append({"snapshot": snapshot, "generated_at": generated_at})
        return KafkaDeliveryReceipt(
            event_id=f"weather-{len(self.weather_calls)}",
            topic="gridd.backend.ai_prediction.events",
            zone_code=None,
            partition=0,
            offset=len(self.weather_calls),
        )

    def publish_prediction(self, **payload):
        self.calls.append(payload)
        if payload["zone_code"] in self.errors:
            raise self.errors[payload["zone_code"]]
        return KafkaDeliveryReceipt(
            event_id=payload.get("event_id") or f"event-{len(self.calls)}",
            topic="gridd.backend.ai_prediction.events",
            zone_code=payload["zone_code"],
            partition=0,
            offset=len(self.calls),
        )


def snapshot_for(zone_code, now):
    observed_at = now - timedelta(minutes=2)
    received_at = now - timedelta(minutes=1)
    zone = ZoneObservations(
        zone_code=zone_code,
        temperature=MetricObservation(22.5, "C", observed_at, received_at, "normal"),
        humidity=MetricObservation(45.0, "%", observed_at, received_at, "normal"),
    )
    weather_at = now - timedelta(minutes=1)
    weather = WeatherSnapshot(
        current=WeatherPoint(weather_at, 18.2, 62.0),
        forecast_h1=WeatherPoint(weather_at + timedelta(hours=1), 17.0, 65.0),
    )
    return CollectionSnapshot(now, weather, {zone_code: zone})


class PredictionOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 15, 19, 0, tzinfo=timezone.utc)
        self.snapshots = {
            zone_code: snapshot_for(zone_code, self.now)
            for zone_code in ZONE_MODEL_MAPPING.values()
        }
        self.collection = FakeCollection(self.snapshots)
        self.predictor = FakePredictor()
        self.producer = FakeProducer()
        self.orchestrator = PredictionOrchestrator(
            collection=self.collection,
            predictor=self.predictor,
            registry=FakeRegistry(),
            producer=self.producer,
            now=lambda: self.now,
        )

    def test_runs_all_six_zones_with_confirmed_feature_order_and_model_hashes(self):
        result = self.orchestrator.run_all()

        zone_codes = tuple(ZONE_MODEL_MAPPING.values())
        self.assertEqual(tuple(item.zone_code for item in result.successes), zone_codes)
        self.assertEqual(result.failures, ())
        self.assertEqual(self.collection.calls, [(zone_code,) for zone_code in zone_codes])
        self.assertEqual(tuple(zone for zone, _features in self.predictor.calls), zone_codes)
        self.assertEqual(len(self.producer.weather_calls), 1)
        self.assertEqual(len(self.producer.calls), 6)
        expected_features = [
            ("indoor_temperature", 22.5),
            ("indoor_humidity", 45.0),
            ("outdoor_temperature", 18.2),
            ("outdoor_humidity", 62.0),
        ]
        self.assertEqual(list(self.predictor.calls[0][1].items()), expected_features)

        for number, prediction in enumerate(result.successes, start=1):
            with self.subTest(zone=prediction.zone_code):
                input_at = self.snapshots[prediction.zone_code].weather.current.timestamp_utc
                self.assertEqual(prediction.input_at, input_at)
                self.assertEqual(prediction.target_at, input_at + timedelta(hours=1))
                self.assertEqual(prediction.prediction_mode, "experimental")
                self.assertEqual(
                    prediction.model_version,
                    f"modelZone{number}:sha256:{number:064x}",
                )
                self.assertEqual(prediction.receipt.zone_code, prediction.zone_code)
                self.assertEqual(self.producer.calls[number - 1]["target_at"], prediction.target_at)

    def test_accepts_subsecond_sensor_clock_skew(self):
        zone_code = "open-workspace"
        original = self.snapshots[zone_code]
        observation = original.zones[zone_code].temperature
        adjusted = replace(
            observation,
            observed_at=observation.received_at + timedelta(milliseconds=100),
        )
        self.collection.snapshots[zone_code] = replace(
            original,
            zones={
                zone_code: replace(original.zones[zone_code], temperature=adjusted),
            },
        )

        prediction = self.orchestrator.run_zone(zone_code)

        self.assertEqual(prediction.zone_code, zone_code)
        self.assertEqual(len(self.producer.calls), 1)

    def test_missing_stale_incoherent_or_invalid_inputs_are_not_published(self):
        zone_code = "open-workspace"
        original = self.snapshots[zone_code]
        bad_cases = {
            "missing zone": replace(original, zones={}),
            "missing observed_at": replace(
                original,
                zones={
                    zone_code: replace(
                        original.zones[zone_code],
                        temperature=replace(original.zones[zone_code].temperature, observed_at=None),
                    )
                },
            ),
            "stale temperature": replace(
                original,
                zones={
                    zone_code: replace(
                        original.zones[zone_code],
                        temperature=replace(
                            original.zones[zone_code].temperature,
                            observed_at=self.now - timedelta(minutes=20),
                            received_at=self.now - timedelta(minutes=19),
                        ),
                    )
                },
            ),
            "incoherent timestamps": replace(
                original,
                zones={
                    zone_code: replace(
                        original.zones[zone_code],
                        temperature=replace(
                            original.zones[zone_code].temperature,
                            observed_at=self.now - timedelta(minutes=9),
                            received_at=self.now - timedelta(minutes=8),
                        ),
                    )
                },
            ),
            "sensor timestamp beyond receipt tolerance": replace(
                original,
                zones={
                    zone_code: replace(
                        original.zones[zone_code],
                        temperature=replace(
                            original.zones[zone_code].temperature,
                            observed_at=original.zones[zone_code].temperature.received_at
                            + timedelta(seconds=2),
                        ),
                    )
                },
            ),
            "non-normal observation quality": replace(
                original,
                zones={
                    zone_code: replace(
                        original.zones[zone_code],
                        humidity=replace(
                            original.zones[zone_code].humidity,
                            quality_status="warning",
                        ),
                    )
                },
            ),
            "wrong unit": replace(
                original,
                zones={
                    zone_code: replace(
                        original.zones[zone_code],
                        humidity=replace(original.zones[zone_code].humidity, unit="g/kg"),
                    )
                },
            ),
        }

        for label, snapshot in bad_cases.items():
            with self.subTest(label=label):
                self.collection.snapshots[zone_code] = snapshot
                with self.assertRaises(PredictionInputError):
                    self.orchestrator.run_zone(zone_code)
                self.assertEqual(self.producer.calls, [])

    def test_collection_error_for_one_zone_does_not_block_the_other_zones(self):
        failed_zone = "meeting-room"
        self.collection.errors[failed_zone] = OpenMeteoError("weather endpoint unavailable")

        with self.assertLogs("ai_prediction_service.services.orchestrator", level="ERROR"):
            result = self.orchestrator.run_all()

        self.assertEqual(len(result.successes), 5)
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(result.failures[0].zone_code, failed_zone)
        self.assertEqual(result.failures[0].error_type, "OpenMeteoError")
        self.assertEqual(len(self.producer.calls), 5)
        self.assertEqual(len(self.collection.calls), 6)

    def test_invalid_predictions_and_prediction_errors_do_not_publish(self):
        zone_code = "open-workspace"
        self.predictor.errors[zone_code] = RuntimeError("model inference failed")
        self.predictor.outputs["server-equipment-room"] = (23.0, 101.0)

        with self.assertLogs("ai_prediction_service.services.orchestrator", level="ERROR"):
            result = self.orchestrator.run_all()

        self.assertEqual(len(result.successes), 4)
        failures = {failure.zone_code: failure.error_type for failure in result.failures}
        self.assertEqual(failures[zone_code], "RuntimeError")
        self.assertEqual(failures["server-equipment-room"], "PredictionInputError")
        self.assertEqual(len(self.producer.weather_calls), 1)
        published_zones = {call["zone_code"] for call in self.producer.calls}
        self.assertNotIn(zone_code, published_zones)
        self.assertNotIn("server-equipment-room", published_zones)

    def test_kafka_error_is_reported_and_other_zones_continue(self):
        failed_zone = "professors-office"
        self.producer.errors[failed_zone] = PredictionPublicationError("local broker rejected event")

        with self.assertLogs("ai_prediction_service.services.orchestrator", level="ERROR"):
            result = self.orchestrator.run_all()

        self.assertEqual(len(result.successes), 5)
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(result.failures[0].zone_code, failed_zone)
        self.assertEqual(result.failures[0].error_type, "PredictionPublicationError")
        self.assertEqual(len(self.producer.calls), 6)

    def test_published_zone_and_input_are_skipped_on_repeat(self):
        zone_code = "open-workspace"
        with TemporaryDirectory() as temp_dir:
            ledger = SQLitePredictionLedger(f"{temp_dir}/predictions.sqlite3")
            orchestrator = PredictionOrchestrator(
                collection=self.collection,
                predictor=self.predictor,
                registry=FakeRegistry(),
                producer=self.producer,
                ledger=ledger,
                now=lambda: self.now,
            )

            first = orchestrator.run_zone(zone_code)
            repeated = orchestrator.run_zone(zone_code)

        self.assertIsNotNone(first)
        self.assertIsNone(repeated)
        self.assertEqual(len(self.predictor.calls), 1)
        self.assertEqual(len(self.producer.calls), 1)

    def test_failed_publication_replays_the_same_event_after_ledger_restart(self):
        zone_code = "open-workspace"
        self.producer.errors[zone_code] = PredictionPublicationError("temporary Kafka outage")
        with TemporaryDirectory() as temp_dir:
            ledger_path = f"{temp_dir}/predictions.sqlite3"
            orchestrator = PredictionOrchestrator(
                collection=self.collection,
                predictor=self.predictor,
                registry=FakeRegistry(),
                producer=self.producer,
                ledger=SQLitePredictionLedger(ledger_path),
                now=lambda: self.now,
            )
            with self.assertRaises(PredictionPublicationError):
                orchestrator.run_zone(zone_code)

            first_attempt = self.producer.calls[0]
            self.producer.errors.clear()
            restarted_orchestrator = PredictionOrchestrator(
                collection=self.collection,
                predictor=self.predictor,
                registry=FakeRegistry(),
                producer=self.producer,
                ledger=SQLitePredictionLedger(ledger_path),
                now=lambda: self.now,
            )
            prediction = restarted_orchestrator.run_zone(zone_code)

        self.assertIsNotNone(prediction)
        self.assertEqual(len(self.predictor.calls), 1)
        self.assertEqual(len(self.producer.calls), 2)
        self.assertEqual(self.producer.calls[1]["event_id"], first_attempt["event_id"])
        self.assertEqual(self.producer.calls[1]["generated_at"], first_attempt["generated_at"])
        self.assertEqual(self.producer.calls[1]["target_at"], first_attempt["target_at"])


if __name__ == "__main__":
    unittest.main()
