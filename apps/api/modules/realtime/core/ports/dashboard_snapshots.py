from typing import Protocol


class DashboardSnapshots(Protocol):
    """Relecture des données diffusées après un changement."""

    def alerts(self) -> dict: ...

    def zones(self) -> list[dict]: ...
