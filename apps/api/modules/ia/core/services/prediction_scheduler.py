import logging
import threading
import time
from collections.abc import Callable

from modules.ia.core.domain.scheduler_settings import SchedulerSettings
from modules.ia.core.ports.heartbeat import Heartbeat

logger = logging.getLogger(__name__)


class PredictionScheduler:
    """Runs one prediction cycle immediately, then at a fixed interval.

    Port : ``Heartbeat`` (written at start-up then every
    ``heartbeat_interval_seconds``, read by the container health check).
    """

    def __init__(
        self,
        run_cycle: Callable[[], int | None],
        settings: SchedulerSettings,
        heartbeat: Heartbeat,
        *,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self._run_cycle = run_cycle
        self._settings = settings
        self._heartbeat = heartbeat
        self._monotonic = monotonic

    def run(self, stop_event: threading.Event) -> None:
        self._write_heartbeat()
        heartbeat_stop = threading.Event()
        heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            args=(heartbeat_stop,),
            name="prediction-scheduler-heartbeat",
            daemon=True,
        )
        heartbeat_thread.start()
        next_run = self._monotonic()
        try:
            while not stop_event.is_set():
                delay = max(0.0, next_run - self._monotonic())
                if delay and stop_event.wait(delay):
                    break
                if stop_event.is_set():
                    break

                cycle_started = self._monotonic()
                try:
                    exit_code = self._run_cycle()
                    if exit_code not in (None, 0):
                        logger.error("Prediction cycle exited with status %s; the scheduler will retry.", exit_code)
                except Exception:
                    logger.exception("Prediction cycle failed; the scheduler will retry.")

                next_run = cycle_started + self._settings.interval_seconds
                now = self._monotonic()
                while next_run <= now:
                    next_run += self._settings.interval_seconds
        finally:
            heartbeat_stop.set()
            heartbeat_thread.join(timeout=self._settings.heartbeat_interval_seconds + 1)

    def _heartbeat_loop(self, stop_event: threading.Event) -> None:
        while not stop_event.wait(self._settings.heartbeat_interval_seconds):
            try:
                self._write_heartbeat()
            except OSError:
                logger.exception("Could not update prediction scheduler heartbeat.")

    def _write_heartbeat(self) -> None:
        self._heartbeat.beat()
