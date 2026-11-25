from typing import Protocol


class DatabaseProbe(Protocol):
    """Vérifie que la base de données répond."""

    def available(self) -> bool: ...
