class WeatherSnapshotService:
    """Consultation du dernier instantané météo."""

    def __init__(self, repository):
        """``repository`` : port ``WeatherSnapshotReader``."""
        self._repository = repository

    def latest(self):
        return self._repository.latest()
