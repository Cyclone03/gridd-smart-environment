import os
import sys
import time
from pathlib import Path

from .scheduler import SchedulerSettings


def heartbeat_is_fresh(path: Path, max_age_seconds: float, *, now: float | None = None) -> bool:
    if max_age_seconds <= 0:
        return False
    try:
        modified_at = path.stat().st_mtime
    except OSError:
        return False
    age = (time.time() if now is None else now) - modified_at
    return 0 <= age <= max_age_seconds


def main() -> int:
    settings = SchedulerSettings.from_env()
    if not heartbeat_is_fresh(settings.heartbeat_path, settings.heartbeat_max_age_seconds):
        print("Prediction scheduler heartbeat is missing or stale.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
