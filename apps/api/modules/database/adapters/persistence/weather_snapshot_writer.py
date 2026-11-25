from modules.database.models import WeatherSnapshot


class WeatherSnapshotWriter:
    """Enregistre chaque instantané météo une seule fois par event_id Kafka.

    Adaptateur du port ``WeatherSnapshotStore``.
    """

    def create(self, *, event_id, values):
        return WeatherSnapshot.objects.get_or_create(
            event_id=event_id,
            defaults=values,
        )
