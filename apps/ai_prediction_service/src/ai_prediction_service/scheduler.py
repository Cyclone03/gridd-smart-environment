import logging
import math
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SchedulerSettings:
    interval_seconds: int = 3600
    heartbeat_interval_seconds: float = 30
    heartbeat_max_age_seconds: float = 180
    heartbeat_path: Path = Path.home() / ".gridd-ai-prediction" / "heartbeat"

    def __post_init__(self):
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive.")
        if (
            not math.isfinite(self.heartbeat_interval_seconds)
            or self.heartbeat_interval_seconds <= 0
        ):
            raise ValueError("heartbeat_interval_seconds must be positive and finite.")
        if (
            not math.isfinite(self.heartbeat_max_age_seconds)
            or self.heartbeat_max_age_seconds <= self.heartbeat_interval_seconds
        ):
            raise ValueError("heartbeat_max_age_seconds must exceed the heartbeat interval.")
        if not str(self.heartbeat_path).strip():
            raise ValueError("heartbeat_path must not be empty.")

    @classmethod
    def from_env(cls, environ=None):
        values = os.environ if environ is None else environ
        return cls(
            interval_seconds=_positive_int(values, "AI_PREDICTION_INTERVAL_SECONDS", 3600),
            heartbeat_interval_seconds=_positive_float(
                values, "AI_PREDICTION_HEARTBEAT_INTERVAL_SECONDS", 30
            ),
            heartbeat_max_age_seconds=_positive_float(
                values, "AI_PREDICTION_HEARTBEAT_MAX_AGE_SECONDS", 180
            ),
            heartbeat_path=Path(
                values.get(
                    "AI_PREDICTION_HEARTBEAT_PATH",
                    str(Path.home() / ".gridd-ai-prediction" / "heartbeat"),
                )
            ),
        )


class PredictionScheduler:
    """Runs one prediction cycle immediately, then at a fixed interval."""

    def __init__(
        self,
        run_cycle: Callable[[], int | None],
        settings: SchedulerSettings,
        *,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self._run_cycle = run_cycle
        self._settings = settings
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
        path = self._settings.heartbeat_path
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        temporary_path.write_text(str(time.time()), encoding="ascii")
        os.replace(temporary_path, path)


def _run_cli_cycle() -> int:
    return subprocess.run([sys.executable, "-m", "ai_prediction_service"], check=False).returncode


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = SchedulerSettings.from_env()
    stop_event = threading.Event()

    def request_stop(signum, _frame):
        logger.info("Received signal %s; stopping after the current prediction cycle.", signum)
        stop_event.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    logger.info(
        "Starting hourly prediction scheduler: interval_seconds=%s heartbeat=%s",
        settings.interval_seconds,
        settings.heartbeat_path,
    )
    PredictionScheduler(_run_cli_cycle, settings).run(stop_event)
    return 0


def _positive_int(values, name: str, default: int) -> int:
    raw = values.get(name, str(default))
    try:
        parsed = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer.") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be a positive integer.")
    return parsed


def _positive_float(values, name: str, default: float) -> float:
    raw = values.get(name, str(default))
    try:
        parsed = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive number.") from exc
    if not math.isfinite(parsed) or parsed <= 0:
        raise ValueError(f"{name} must be a positive finite number.")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
