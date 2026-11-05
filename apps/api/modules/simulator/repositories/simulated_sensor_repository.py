from modules.database.models import Observation, Sensor
from modules.simulator.domain.simulated_sensor import SimulatedSensor


class SimulatedSensorRepository:
    """Capteurs actifs à simuler et leur dernière valeur (lecture seule)."""

    def active(self) -> list[SimulatedSensor]:
        return [
            SimulatedSensor(
                node_id=sensor.node_id,
                metric=sensor.sensor_type,
                unit=sensor.unit,
                zone_code=sensor.zone.code,
                zone_name=sensor.zone.name,
                last_value=self._last_value(sensor),
            )
            for sensor in Sensor.objects.filter(active=True).select_related("zone")
        ]

    @staticmethod
    def _last_value(sensor):
        return (
            Observation.objects.filter(sensor=sensor)
            .order_by("-observed_at", "-received_at")
            .values_list("value", flat=True)
            .first()
        )
