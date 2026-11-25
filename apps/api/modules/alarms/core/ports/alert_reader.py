from typing import Protocol


class AlertReader(Protocol):
    """Lecture des alertes, les plus récentes en premier."""

    def search(self, *, limit, zone=None, active=None, rule=None, severity=None, since=None, until=None): ...

    def get(self, alert_id): ...
