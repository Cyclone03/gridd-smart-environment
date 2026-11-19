from modules.database.models import WeatherSnapshot


class WeatherSnapshotRepository:
    """Lecture du dernier instantané météo persisté."""

    def latest(self):
        return WeatherSnapshot.objects.order_by("-generated_at", "-pk").first()
