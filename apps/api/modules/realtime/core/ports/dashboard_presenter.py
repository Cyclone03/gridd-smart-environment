from typing import Protocol


class DashboardPresenter(Protocol):
    """Représentation JSON (mêmes formes que l'API REST) des objets lus par
    le ``DashboardReader``."""

    def zone(self, zone) -> dict: ...

    def observation(self, observation) -> dict: ...

    def alert(self, alert) -> dict: ...
