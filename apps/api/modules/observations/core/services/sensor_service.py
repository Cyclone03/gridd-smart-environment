class SensorService:
    """Consultation des capteurs actifs."""

    def __init__(self, repository):
        """``repository`` : port ``SensorReader``."""
        self._repository = repository

    def list(self, zone_code=None):
        return self._repository.active(zone_code)

    def get(self, sensor_id):
        return self._repository.get(sensor_id)
