from modules.database.models import Sensor


class SensorRepository:
    """Lecture des capteurs actifs (lecture seule)."""

    def active(self, zone_code=None):
        sensors = Sensor.objects.select_related("zone").filter(active=True)
        if zone_code:
            sensors = sensors.filter(zone__code=zone_code)
        return sensors.order_by("zone__name", "sensor_type")

    def get(self, sensor_id) -> Sensor | None:
        try:
            return self.active().filter(pk=int(sensor_id)).first()
        except (TypeError, ValueError):
            return None
