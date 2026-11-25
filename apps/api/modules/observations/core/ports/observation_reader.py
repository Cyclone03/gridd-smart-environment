from typing import Protocol


class ObservationReader(Protocol):
    """Lecture des observations. Les objets retournés exposent au moins
    ``observed_at`` et ``received_at`` ; leur forme est celle attendue par
    l'adaptateur HTTP qui les sérialise."""

    def recent(self, *, zone_code=None, metric=None, limit=1000): ...

    def latest(self, zone, metric): ...

    def active_zones(self): ...

    def get(self, observation_id): ...
