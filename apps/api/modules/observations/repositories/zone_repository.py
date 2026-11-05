from django.db.models import Prefetch

from modules.database.models import Sensor, Zone


class ZoneRepository:
    """Lecture des zones actives (lecture seule)."""

    def active(self):
        return (
            Zone.objects.filter(active=True)
            .select_related("threshold_profile")
            .prefetch_related(
                Prefetch("sensors", queryset=Sensor.objects.filter(active=True), to_attr="active_sensors")
            )
            .order_by("name")
        )

    def get(self, zone_id) -> Zone | None:
        try:
            return self.active().filter(pk=int(zone_id)).first()
        except (TypeError, ValueError):
            return None

    def get_by_code(self, code) -> Zone | None:
        return self.active().filter(code=code).first()
