import json
import unittest
from datetime import datetime, timedelta, timezone
from uuid import UUID

from ai_prediction_service.domain.weather import WeatherPoint, WeatherSnapshot
from ai_prediction_service.messaging.weather_snapshot_event import (
    WEATHER_PROVIDER,
    WEATHER_SNAPSHOT_EVENT_SOURCE,
    WEATHER_SNAPSHOT_EVENT_TYPE,
    WeatherSnapshotEvent,
)


class WeatherSnapshotEventTests(unittest.TestCase):
    def setUp(self):
        self.generated_at = datetime(2026, 11, 15, 18, 5, tzinfo=timezone.utc)
        self.snapshot = WeatherSnapshot(
            current=WeatherPoint(self.generated_at - timedelta(minutes=5), 18.2, 62.0),
            forecast_h1=WeatherPoint(self.generated_at + timedelta(minutes=55), 17.0, 65.0),
        )

    def test_builds_a_backend_compatible_event_with_the_actual_weather_fields(self):
        event = WeatherSnapshotEvent.create(snapshot=self.snapshot, generated_at=self.generated_at)
        decoded = json.loads(event.encode().decode("utf-8"))

        self.assertEqual(decoded["type"], WEATHER_SNAPSHOT_EVENT_TYPE)
        self.assertEqual(decoded["source"], WEATHER_SNAPSHOT_EVENT_SOURCE)
        self.assertEqual(str(UUID(decoded["event_id"])), decoded["event_id"])
        self.assertEqual(decoded["occurred_at"], self.generated_at.isoformat())
        self.assertEqual(decoded["payload"]["generated_at"], self.generated_at.isoformat())
        self.assertEqual(decoded["payload"]["provider"], WEATHER_PROVIDER)
        self.assertEqual(decoded["payload"]["current_at"], self.snapshot.current.timestamp_utc.isoformat())
        self.assertEqual(decoded["payload"]["current_temperature_c"], 18.2)
        self.assertEqual(decoded["payload"]["current_relative_humidity_percent"], 62.0)
        self.assertEqual(decoded["payload"]["forecast_h1_at"], self.snapshot.forecast_h1.timestamp_utc.isoformat())
        self.assertEqual(decoded["payload"]["forecast_h1_temperature_c"], 17.0)
        self.assertEqual(decoded["payload"]["forecast_h1_relative_humidity_percent"], 65.0)
        self.assertIsNone(decoded["correlation_id"])
        self.assertIsNone(decoded["reply_to"])

    def test_rejects_naive_or_non_future_timestamps_and_invalid_weather_values(self):
        invalid_snapshots = (
            WeatherSnapshot(
                self.snapshot.current,
                WeatherPoint(self.snapshot.current.timestamp_utc, 17.0, 65.0),
            ),
            WeatherSnapshot(
                self.snapshot.current,
                WeatherPoint(self.generated_at, 17.0, 65.0),
            ),
            WeatherSnapshot(
                self.snapshot.current,
                WeatherPoint(self.snapshot.forecast_h1.timestamp_utc, 17.0, 101.0),
            ),
            WeatherSnapshot(
                self.snapshot.current,
                WeatherPoint(
                    self.snapshot.forecast_h1.timestamp_utc,
                    float("nan"),
                    65.0,
                ),
            ),
        )
        for snapshot in invalid_snapshots:
            with self.subTest(snapshot=snapshot), self.assertRaises(ValueError):
                WeatherSnapshotEvent.create(snapshot=snapshot, generated_at=self.generated_at)

        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            WeatherSnapshotEvent.create(
                snapshot=self.snapshot,
                generated_at=datetime(2026, 11, 15, 18, 5),
            )

        with self.assertRaisesRegex(ValueError, "forecast_h1_at"):
            WeatherSnapshotEvent.create(
                snapshot=self.snapshot,
                generated_at=self.snapshot.forecast_h1.timestamp_utc,
            )


if __name__ == "__main__":
    unittest.main()
