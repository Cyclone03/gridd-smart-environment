import random
import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Sensor
from core.services import ingest_observation


class Command(BaseCommand):
    help = "Génère des observations de test progressives par zone"

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=float, default=30.0)

    def initial_value(self, sensor):
        latest = sensor.observations.order_by("-observed_at", "-received_at").first()
        if latest:
            return latest.value
        defaults = {
            "temperature": 22.0,
            "humidity": 42.0,
            "co2": 600.0,
            "sound_level": 42.0,
            "occupancy": 4.0,
        }
        return defaults[sensor.sensor_type]

    def next_value(self, sensor_type, current):
        settings = {
            "temperature": (0.12, 18.0, 28.0, 1),
            "humidity": (0.4, 25.0, 70.0, 1),
            "co2": (8.0, 400.0, 1600.0, 0),
            "sound_level": (0.8, 30.0, 85.0, 1),
            "occupancy": (1.0, 0.0, 35.0, 0),
        }
        step, minimum, maximum, digits = settings[sensor_type]
        if sensor_type == "occupancy":
            value = current + random.choice([-1, 0, 0, 0, 1])
        else:
            value = current + random.uniform(-step, step)
        return round(min(max(value, minimum), maximum), digits)

    def handle(self, *args, **options):
        interval = options["interval"]
        sensors = list(Sensor.objects.filter(active=True).select_related("zone"))
        current_values = {sensor.pk: self.initial_value(sensor) for sensor in sensors}
        self.stdout.write("Simulateur GRIDD démarré. Ctrl+C pour arrêter.")
        try:
            while True:
                for sensor in sensors:
                    value = self.next_value(sensor.sensor_type, current_values[sensor.pk])
                    current_values[sensor.pk] = value

                    ingest_observation(
                        node_id=sensor.node_id,
                        observation_type=sensor.sensor_type,
                        value=value,
                        unit=sensor.unit,
                        observed_at=timezone.now(),
                        metadata={
                            "source": "simulator",
                            "zone": {
                                "id": sensor.zone.code,
                                "label": sensor.zone.name,
                            },
                        },
                    )
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write("\nSimulateur arrêté.")
