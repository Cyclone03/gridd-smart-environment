class AlertQueryService:
    """Consultation des alertes et de l'historique des épisodes d'alarme.

    Port : ``AlertReader``.
    """

    DEFAULT_LIMIT = 500

    def __init__(self, repository):
        self._repository = repository

    def search(self, *, active=None, limit=DEFAULT_LIMIT, **filters):
        flag = {"true": True, "false": False}.get(active)
        return self._repository.search(active=flag, limit=limit, **filters)

    def get(self, alert_id):
        return self._repository.get(alert_id)
