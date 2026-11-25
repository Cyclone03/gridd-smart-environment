from typing import Protocol


class DashboardReader(Protocol):
    """Lecture des données du tableau de bord (objets bruts, présentés par
    un ``DashboardPresenter``)."""

    def zones(self) -> list: ...

    def latest_observations(self, zones) -> list: ...

    def active_alerts(self, limit) -> list: ...

    def resolved_alerts(self, *, days, limit) -> list: ...
