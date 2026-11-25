from typing import Protocol


class QualityAlertStates(Protocol):
    """Alertes de qualité actives par (zone, code)."""

    def is_active(self, zone_code, code) -> bool: ...

    def remember(self, zone_code, code, active: bool) -> None: ...

    def should_refresh(self, zone_code, code, status, moment) -> bool: ...
