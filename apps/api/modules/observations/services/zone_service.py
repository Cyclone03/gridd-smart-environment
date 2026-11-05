from modules.observations.repositories.zone_repository import ZoneRepository


class ZoneService:
    """Consultation des zones (espaces) actives."""

    def __init__(self, repository=None):
        self._repository = repository or ZoneRepository()

    def list(self):
        return self._repository.active()

    def get(self, zone_id):
        return self._repository.get(zone_id)
