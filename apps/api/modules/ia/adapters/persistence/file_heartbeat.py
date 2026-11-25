import os
import time
from pathlib import Path


class FileHeartbeat:
    """Adaptateur fichier du port ``Heartbeat`` : horodatage écrit de façon
    atomique, dont l'âge est vérifié par ``ai_prediction_healthcheck``."""

    def __init__(self, path):
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def beat(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self._path.with_name(f"{self._path.name}.{os.getpid()}.tmp")
        temporary_path.write_text(str(time.time()), encoding="ascii")
        os.replace(temporary_path, self._path)

    def is_fresh(self, max_age_seconds: float, *, now: float | None = None) -> bool:
        if max_age_seconds <= 0:
            return False
        try:
            modified_at = self._path.stat().st_mtime
        except OSError:
            return False
        age = (time.time() if now is None else now) - modified_at
        return 0 <= age <= max_age_seconds
