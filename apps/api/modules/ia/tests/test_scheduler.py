import threading
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase, override_settings

from modules.ia import composition
from modules.ia.adapters.persistence.file_heartbeat import FileHeartbeat
from modules.ia.core.domain.scheduler_settings import SchedulerSettings
from modules.ia.core.services.prediction_scheduler import PredictionScheduler


class SchedulerSettingsTests(SimpleTestCase):
    def test_defaults_to_one_hour_and_accepts_a_configurable_interval(self):
        self.assertEqual(composition.scheduler_settings().interval_seconds, 3600)
        with override_settings(AI_PREDICTION_INTERVAL_SECONDS=900, AI_PREDICTION_HEARTBEAT_PATH="/tmp/prediction-heartbeat"):
            configured = composition.scheduler_settings()

        self.assertEqual(configured.interval_seconds, 900)
        self.assertEqual(configured.heartbeat_path, Path("/tmp/prediction-heartbeat"))

    def test_rejects_non_positive_schedule_and_heartbeat_intervals(self):
        for values in (
            {"interval_seconds": 0},
            {"heartbeat_interval_seconds": -1},
            {"heartbeat_max_age_seconds": float("nan")},
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                SchedulerSettings(**values)


class PredictionSchedulerTests(SimpleTestCase):
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
                FileHeartbeat(heartbeat),
            )
            with self.assertLogs("modules.ia.core.services.prediction_scheduler", level="ERROR"):
                scheduler.run(stop_event)

            self.assertTrue(FileHeartbeat(heartbeat).is_fresh(1))

        self.assertEqual(len(calls), 2)
        self.assertGreaterEqual(calls[1] - calls[0], 0.008)

    def test_healthcheck_rejects_missing_stale_and_future_heartbeats(self):
        with TemporaryDirectory() as temp_dir:
            heartbeat = Path(temp_dir) / "heartbeat"

            probe = FileHeartbeat(heartbeat)
            self.assertFalse(probe.is_fresh(10, now=100))
            heartbeat.touch()
            self.assertFalse(probe.is_fresh(10, now=heartbeat.stat().st_mtime + 11))
            self.assertFalse(probe.is_fresh(10, now=heartbeat.stat().st_mtime - 1))
            self.assertTrue(probe.is_fresh(10, now=heartbeat.stat().st_mtime + 1))
