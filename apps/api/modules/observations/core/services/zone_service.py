class ZoneService:
    """Consultation des zones (espaces) actives."""

    def __init__(self, repository):
        """``repository`` : port ``ZoneReader``."""
        self._repository = repository

    def list(self):
        return self._repository.active()

    def get(self, zone_id):
        return self._repository.get(zone_id)
