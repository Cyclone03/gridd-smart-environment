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


class SchedulerAlignmentTests(SimpleTestCase):
    """Les cycles démarrent juste après un quart d'heure : l'écart avec les
    conditions courantes d'Open-Meteo (pas de 15 min) reste sous 5 minutes."""

    def scheduler(self, wall_now, monotonic_now=1000.0):
        return PredictionScheduler(
            lambda: 0,
            SchedulerSettings(align_seconds=900, align_offset_seconds=60),
            FileHeartbeat("/tmp/unused"),
            monotonic=lambda: monotonic_now,
            wall_clock=lambda: wall_now,
        )

    def test_waits_for_the_next_quarter_hour_plus_offset(self):
        quarter = 1_795_623_300.0  # 2026-11-25 16:15:00 UTC
        scheduler = self.scheduler(wall_now=quarter + 7 * 60 + 32)  # 16:22:32
        with self.assertLogs("modules.ia.core.services.prediction_scheduler", level="INFO"):
            next_run = scheduler.next_run_after(1000.0)
        self.assertAlmostEqual(next_run - 1000.0, (quarter + 900 + 60) - (quarter + 452))

    def test_runs_now_when_already_on_a_slot_and_keeps_the_interval_aligned(self):
        slot = 1_795_623_300.0 + 60
        scheduler = self.scheduler(wall_now=slot)
        with self.assertLogs("modules.ia.core.services.prediction_scheduler", level="INFO"):
            self.assertAlmostEqual(scheduler.next_run_after(1000.0), 1000.0)
            self.assertAlmostEqual(scheduler.next_run_after(1000.0 + 3600), 1000.0 + 3600)

    def test_alignment_settings_are_validated(self):
        with self.assertRaises(ValueError):
            SchedulerSettings(align_seconds=900, align_offset_seconds=900)
        with self.assertRaises(ValueError):
            SchedulerSettings(align_seconds=-1)
