from modules.alarms.repositories.alert_repository import AlertRepository


class AlertQueryService:
    """Consultation des alertes et de l'historique des épisodes d'alarme."""

    DEFAULT_LIMIT = 500

    def __init__(self, repository=None):
        self._repository = repository or AlertRepository()

    def search(self, *, active=None, limit=DEFAULT_LIMIT, **filters):
        flag = {"true": True, "false": False}.get(active)
        return self._repository.search(active=flag, **filters).order_by("-created_at")[:limit]

    def get(self, alert_id):
        return self._repository.get(alert_id)
