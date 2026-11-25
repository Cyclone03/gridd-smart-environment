from typing import Protocol


class HistoryReader(Protocol):
    """Lecture des mesures d'une zone (implémentée par un adaptateur de persistance)."""

    def active_zone(self, code):
        """Zone active (objet exposant ``code``) ou ``None``."""

    def rows(self, zone, metric, period):
        """Itérable de ``{value, observed_at, received_at, quality_status}`` dans
        ``[period.start ; period.end[``, triés chronologiquement."""
