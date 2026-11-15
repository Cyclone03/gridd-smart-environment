from django.conf import settings

from modules.realtime.mappers.dashboard_payload_mapper import DashboardPayloadMapper
from modules.realtime.repositories.dashboard_repository import DashboardRepository


class DashboardSnapshotService:
    """Données du tableau de bord poussées sur ``/ws/dashboard/``.

    - ``snapshot()`` : état complet envoyé à la connexion (et sur demande) ;
    - ``alerts()`` : alertes actives + historique récent, après ``alerts.changed`` ;
    - ``zones()`` : zones actives, après ``zones.changed``.

    Le navigateur n'a donc plus à interroger ``/api/zones/``,
    ``/api/observations/latest/`` ni ``/api/alerts/`` à intervalle régulier.
    """

    ACTIVE_ALERTS_LIMIT = 500

    def __init__(self, repository=None, mapper=None, *, history_days=None, history_limit=None):
        self._repository = repository or DashboardRepository()
        self._mapper = mapper or DashboardPayloadMapper()
        self._history_days = history_days or settings.REALTIME_ALERT_HISTORY_DAYS
        self._history_limit = history_limit or settings.REALTIME_ALERT_HISTORY_LIMIT

    def snapshot(self) -> dict:
        zones = self._repository.zones()
        return {
            "zones": [self._mapper.zone(zone) for zone in zones],
            "latest": [self._mapper.observation(item) for item in self._repository.latest_observations(zones)],
            "alerts": self.alerts(),
        }

    def zones(self) -> list[dict]:
        return [self._mapper.zone(zone) for zone in self._repository.zones()]

    def alerts(self) -> dict:
        return {
            "active": [self._mapper.alert(alert) for alert in self._repository.active_alerts(self.ACTIVE_ALERTS_LIMIT)],
            "history": [
                self._mapper.alert(alert)
                for alert in self._repository.resolved_alerts(days=self._history_days, limit=self._history_limit)
            ],
            "history_days": self._history_days,
        }
