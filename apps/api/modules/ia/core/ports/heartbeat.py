from typing import Protocol


class Heartbeat(Protocol):
    """Signal de vie du planificateur (lu par le contrôle de santé du conteneur)."""

    def beat(self) -> None: ...
