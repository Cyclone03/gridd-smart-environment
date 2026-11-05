import json

from django.utils import timezone

from modules.simulator.domain.value_generator import ValueGenerator
from modules.simulator.repositories.simulated_sensor_repository import SimulatedSensorRepository
from shared.contracts.topics import Topics
from shared.messaging import Messaging


class SimulatorService:
    """Joue le rôle des capteurs : publie des mesures au format GRIDD sur les
    topics capteurs. Elles suivent ensuite exactement le même chemin que les
    mesures réelles (ingestion → database → alarms / realtime)."""

    def __init__(self, repository, generator, publisher):
        self._repository = repository
        self._generator = generator
        self._publisher = publisher
        self._sensors = []
        self._values = {}

    @classmethod
    def build(cls):
        return cls(SimulatedSensorRepository(), ValueGenerator(), Messaging.current().publisher("sensors"))

    def start(self) -> int:
        self._sensors = [sensor for sensor in self._repository.active() if Topics.sensor_topic_for(sensor.metric)]
        self._values = {
            (sensor.node_id, sensor.metric): self._generator.initial(sensor.metric, sensor.last_value)
            for sensor in self._sensors
        }
        return len(self._sensors)

    def tick(self) -> int:
        observed_at = timezone.now().isoformat()
        for sensor in self._sensors:
            key = (sensor.node_id, sensor.metric)
            self._values[key] = self._generator.next(sensor.metric, self._values[key])
            message = {
                "node_id": sensor.node_id,
                "type": sensor.metric,
                "value": self._values[key],
                "unit": sensor.unit,
                "timestamp": observed_at,
                "metadata": {
                    "source": "simulator",
                    "zone": {"id": sensor.zone_code, "label": sensor.zone_name},
                },
            }
            self._publisher.publish_raw(
                Topics.sensor_topic_for(sensor.metric),
                json.dumps(message).encode("utf-8"),
                key=sensor.node_id,
            )
        return len(self._sensors)
