from modules.database.models import Observation, Zone


class ObservationRepository:
    """Lecture des observations (lecture seule).

    Les tris utilisent les index existants (``zone, type, -observed_at`` et
    clé primaire). Un tri ``observed_at DESC NULLS LAST`` ne correspond à
    aucun index sous PostgreSQL (un index DESC range les NULL en premier) :
    il imposait de lire et trier toutes les mesures d'une zone, soit plusieurs
    secondes par requête une fois la table remplie.
    """

    def recent(self, *, zone_code=None, metric=None, limit=1000):
        observations = Observation.objects.select_related("zone", "sensor")
        if zone_code:
            observations = observations.filter(zone__code=zone_code)
        if metric:
            observations = observations.filter(type=metric)
        if zone_code and metric:
            return observations.order_by("-observed_at", "-received_at")[:limit]
        # Sans filtre complet : ordre d'insertion (index de clé primaire).
        return observations.order_by("-pk")[:limit]

    def latest(self, zone, metric) -> Observation | None:
        observations = Observation.objects.filter(zone=zone, type=metric).select_related("zone", "sensor")
        # Parcours de l'index (zone, type, -observed_at) : une seule ligne lue.
        found = observations.filter(observed_at__isnull=False).order_by("-observed_at").first()
        if found is None:
            found = observations.filter(observed_at__isnull=True).order_by("-pk").first()
        return found

    def active_zones(self):
        return Zone.objects.filter(active=True).order_by("name")

    def get(self, observation_id) -> Observation | None:
        try:
            return Observation.objects.select_related("zone", "sensor").filter(pk=int(observation_id)).first()
        except (TypeError, ValueError):
            return None
