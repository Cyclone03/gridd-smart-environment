from modules.database.models import Observation


class ObservationFreshnessRepository:
    """Adaptateur Django du port ``DataFreshnessReader``."""

    def last_received_at(self):
        # Dernière ligne insérée (index de clé primaire : pas de tri sur toute la table).
        return Observation.objects.order_by("-pk").values_list("received_at", flat=True).first()
