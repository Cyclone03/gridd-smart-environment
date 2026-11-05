from modules.observations.repositories.sensor_repository import SensorRepository


class SensorService:
    """Consultation des capteurs actifs."""

    def __init__(self, repository=None):
        self._repository = repository or SensorRepository()

    def list(self, zone_code=None):
        return self._repository.active(zone_code)

    def get(self, sensor_id):
        return self._repository.get(sensor_id)
