from datetime import datetime
from typing import Protocol


class DataFreshnessReader(Protocol):
    """Horodatage de réception de la dernière mesure enregistrée."""

    def last_received_at(self) -> datetime | None: ...
