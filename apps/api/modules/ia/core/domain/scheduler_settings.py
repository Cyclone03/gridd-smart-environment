import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SchedulerSettings:
    interval_seconds: int = 3600
    heartbeat_interval_seconds: float = 30
    heartbeat_max_age_seconds: float = 180
    heartbeat_path: Path = Path("/var/lib/ai-predictions/heartbeat")

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
