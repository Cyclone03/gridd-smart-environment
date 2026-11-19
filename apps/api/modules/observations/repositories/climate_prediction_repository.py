from django.db.models import OuterRef, Subquery

from modules.database.models import ClimatePrediction


class ClimatePredictionRepository:
    """Lecture des dernières prédictions persistées par zone active."""

    def latest_by_zone(self):
        latest_id = (
            ClimatePrediction.objects.filter(zone_id=OuterRef("zone_id"))
            .order_by("-generated_at", "-pk")
            .values("pk")[:1]
        )
        return (
            ClimatePrediction.objects.filter(zone__active=True, pk=Subquery(latest_id))
            .select_related("zone")
            .order_by("zone__code")
        )
