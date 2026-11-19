from modules.observations.repositories.weather_snapshot_repository import WeatherSnapshotRepository


class WeatherSnapshotService:
    def __init__(self, repository=None):
        self._repository = repository or WeatherSnapshotRepository()

    def latest(self):
        return self._repository.latest()
