from modules.simulator.core.domain.value_generator import ValueGenerator
from shared.kernel.timestamps import utc_now


class SimulatorService:
    """Joue le rôle des capteurs : publie des mesures au format GRIDD. Elles
    suivent ensuite exactement le même chemin que les mesures réelles
    (ingestion → database → alarms / realtime).

    Ports : ``SensorSource`` (capteurs à simuler) et ``ReadingPublisher``.
    """

    def __init__(self, *, sensors, publisher, generator=None, clock=utc_now):
        self._sensor_source = sensors
        self._publisher = publisher
        self._generator = generator or ValueGenerator()
        self._clock = clock
        self._sensors = []
        self._values = {}

    def start(self) -> int:
        self._sensors = [sensor for sensor in self._sensor_source.active() if self._publisher.supports(sensor.metric)]
        self._values = {
            (sensor.node_id, sensor.metric): self._generator.initial(sensor.metric, sensor.last_value)
            for sensor in self._sensors
        }
        return len(self._sensors)

    def tick(self) -> int:
        observed_at = self._clock().isoformat()
        for sensor in self._sensors:
            key = (sensor.node_id, sensor.metric)
            self._values[key] = self._generator.next(sensor.metric, self._values[key])
            self._publisher.publish(
                sensor.metric,
                sensor.node_id,
                {
                    "node_id": sensor.node_id,
                    "type": sensor.metric,
                    "value": self._values[key],
                    "unit": sensor.unit,
                    "timestamp": observed_at,
                    "metadata": {
                        "source": "simulator",
                        "zone": {"id": sensor.zone_code, "label": sensor.zone_name},
                    },
                },
            )
        return len(self._sensors)
