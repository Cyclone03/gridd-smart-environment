import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import time

from ai_prediction_service.healthcheck import heartbeat_is_fresh
from ai_prediction_service.scheduler import PredictionScheduler, SchedulerSettings


class SchedulerSettingsTests(unittest.TestCase):
    def test_defaults_to_one_hour_and_accepts_a_configurable_interval(self):
        defaults = SchedulerSettings.from_env({})
        configured = SchedulerSettings.from_env(
            {
                "AI_PREDICTION_INTERVAL_SECONDS": "900",
                "AI_PREDICTION_HEARTBEAT_PATH": "/tmp/prediction-heartbeat",
            }
        )

        self.assertEqual(defaults.interval_seconds, 3600)
        self.assertEqual(configured.interval_seconds, 900)
        self.assertEqual(configured.heartbeat_path, Path("/tmp/prediction-heartbeat"))

    def test_rejects_non_positive_schedule_and_heartbeat_intervals(self):
        for values in (
            {"AI_PREDICTION_INTERVAL_SECONDS": "0"},
            {"AI_PREDICTION_HEARTBEAT_INTERVAL_SECONDS": "-1"},
            {"AI_PREDICTION_HEARTBEAT_MAX_AGE_SECONDS": "nan"},
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                SchedulerSettings.from_env(values)


class PredictionSchedulerTests(unittest.TestCase):
    def test_runs_immediately_and_continues_after_a_failed_cycle(self):
        calls = []
        stop_event = threading.Event()

        def run_cycle():
            calls.append(time.monotonic())
            if len(calls) == 1:
                return 1
            stop_event.set()
            return 0

        with TemporaryDirectory() as temp_dir:
            heartbeat = Path(temp_dir) / "heartbeat"
            scheduler = PredictionScheduler(
                run_cycle,
                SchedulerSettings(
                    interval_seconds=0.01,
                    heartbeat_interval_seconds=0.002,
                    heartbeat_max_age_seconds=1,
                    heartbeat_path=heartbeat,
                ),
            )
            with self.assertLogs("ai_prediction_service.scheduler", level="ERROR"):
                scheduler.run(stop_event)

            self.assertTrue(heartbeat_is_fresh(heartbeat, 1))

        self.assertEqual(len(calls), 2)
        self.assertGreaterEqual(calls[1] - calls[0], 0.008)

    def test_healthcheck_rejects_missing_stale_and_future_heartbeats(self):
        with TemporaryDirectory() as temp_dir:
            heartbeat = Path(temp_dir) / "heartbeat"

            self.assertFalse(heartbeat_is_fresh(heartbeat, 10, now=100))
            heartbeat.touch()
            self.assertFalse(heartbeat_is_fresh(heartbeat, 10, now=heartbeat.stat().st_mtime + 11))
            self.assertFalse(heartbeat_is_fresh(heartbeat, 10, now=heartbeat.stat().st_mtime - 1))


if __name__ == "__main__":
    unittest.main()
