from modules.database.models import ClimatePrediction


class ClimatePredictionWriter:
    """Enregistre chaque prédiction une seule fois par event_id Kafka."""

    def create(self, *, event_id, zone, values):
        return ClimatePrediction.objects.get_or_create(
            event_id=event_id,
            defaults={"zone": zone, **values},
        )
