import json
import unittest
from datetime import datetime, timedelta, timezone
from uuid import UUID

from modules.ia.core.domain.climate_prediction_event import (
    PREDICTION_EVENT_SOURCE,
    PREDICTION_EVENT_TYPE,
    ClimatePredictionEvent,
)


class ClimatePredictionEventTests(unittest.TestCase):
    def create_event(self, **overrides):
        values = {
            "zone_code": "open-workspace",
            "generated_at": datetime(2026, 11, 15, 18, tzinfo=timezone.utc),
            "target_at": datetime(2026, 11, 15, 19, tzinfo=timezone.utc),
            "predicted_temperature_c": 23.5,
            "predicted_humidity_percent": 45.0,
            "model_version": "sha256:0123456789abcdef",
            "prediction_mode": "experimental",
        }
        values.update(overrides)
        return ClimatePredictionEvent.create(**values)

    def test_builds_backend_compatible_event_with_utc_timestamps(self):
        event = self.create_event(
            target_at=datetime(2026, 11, 15, 14, tzinfo=timezone(timedelta(hours=-5)))
        )
        encoded = event.to_event().encode()
        decoded = json.loads(encoded.decode("utf-8"))

        self.assertEqual(decoded["type"], PREDICTION_EVENT_TYPE)
        self.assertEqual(decoded["source"], PREDICTION_EVENT_SOURCE)
        self.assertEqual(str(UUID(decoded["event_id"])), decoded["event_id"])
        self.assertEqual(decoded["occurred_at"], "2026-11-15T18:00:00+00:00")
        self.assertEqual(decoded["payload"]["generated_at"], decoded["occurred_at"])
        self.assertEqual(decoded["payload"]["target_at"], "2026-11-15T19:00:00+00:00")
        self.assertEqual(decoded["payload"]["zone_code"], "open-workspace")
        self.assertEqual(decoded["payload"]["predicted_temperature_c"], 23.5)
        self.assertEqual(decoded["payload"]["predicted_humidity_percent"], 45.0)
        self.assertEqual(decoded["payload"]["model_version"], "sha256:0123456789abcdef")
        self.assertEqual(decoded["payload"]["prediction_mode"], "experimental")
        self.assertIsNone(decoded["correlation_id"])
        self.assertIsNone(decoded["reply_to"])

    def test_rejects_unknown_zone_naive_or_past_target_and_missing_model_version(self):
        generated_at = datetime(2026, 11, 15, 18, tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError, "Unknown prediction zone"):
            self.create_event(zone_code="unknown-zone")
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            self.create_event(target_at=datetime(2026, 11, 15, 19))
        with self.assertRaisesRegex(ValueError, "later than"):
            self.create_event(target_at=generated_at)
        with self.assertRaisesRegex(ValueError, "model_version"):
            self.create_event(model_version=" ")

    def test_rejects_invalid_modes_and_non_finite_or_non_numeric_predictions(self):
        for field, value in (
            ("prediction_mode", "unknown"),
            ("prediction_mode", None),
            ("predicted_temperature_c", "23.5"),
            ("predicted_temperature_c", float("nan")),
            ("predicted_humidity_percent", float("inf")),
            ("predicted_humidity_percent", True),
        ):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.create_event(**{field: value})

    def test_accepts_a_stable_event_id_for_idempotent_retries(self):
        event_id = "7e692bb9-0e5c-4bee-87a4-9fde0e305694"
        event = self.create_event(event_id=event_id)

        self.assertEqual(event.event_id, event_id)
        with self.assertRaisesRegex(ValueError, "event_id"):
            self.create_event(event_id="not-a-uuid")
