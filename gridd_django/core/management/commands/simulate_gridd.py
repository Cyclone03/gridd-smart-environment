import random
import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Sensor
from core.services import ingest_observation


class Command(BaseCommand):
    help = "Génère des observations de test par zone"

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=float, default=2.0)

    def handle(self, *args, **options):
        interval = options["interval"]
        self.stdout.write("Simulateur GRIDD démarré. Ctrl+C pour arrêter.")
        try:
            while True:
                for sensor in Sensor.objects.filter(active=True).select_related("zone"):
                    if sensor.sensor_type == "temperature":
                        value = round(random.uniform(19, 30), 1)
                    elif sensor.sensor_type == "humidity":
                        value = round(random.uniform(25, 70), 1)
                    elif sensor.sensor_type == "co2":
                        value = round(random.uniform(450, 1500), 0)
                    elif sensor.sensor_type == "sound_level":
                        value = round(random.uniform(35, 80), 1)
                    else:
                        value = random.randint(0, 35)

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
