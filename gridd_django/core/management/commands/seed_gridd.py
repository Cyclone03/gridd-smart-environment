from django.core.management.base import BaseCommand
from core.models import Zone, ThresholdProfile, Sensor


class Command(BaseCommand):
    help = "Crée des zones et capteurs de démonstration"

    def handle(self, *args, **options):
        zones = [
            ("Salle serveur", "salle-serveur", Zone.ZoneType.SERVER_ROOM),
            ("Salle de cours", "salle-cours", Zone.ZoneType.CLASSROOM),
            ("Bureau professeur", "bureau-prof", Zone.ZoneType.OFFICE),
        ]

        for name, code, zone_type in zones:
            zone, _ = Zone.objects.get_or_create(
                code=code,
                defaults={"name": name, "zone_type": zone_type},
            )
            ThresholdProfile.objects.get_or_create(zone=zone)

            sensor_defs = [
                ("temperature", "°C"),
                ("humidity", "%"),
                ("co2", "ppm"),
                ("sound_level", "dBA"),
                ("occupancy", "count"),
            ]
            for sensor_type, unit in sensor_defs:
                Sensor.objects.get_or_create(
                    node_id=f"{code}-{sensor_type}",
                    defaults={
                        "label": f"{name} — {sensor_type}",
                        "sensor_type": sensor_type,
                        "zone": zone,
                        "unit": unit,
                    },
                )

        self.stdout.write(self.style.SUCCESS("Zones et capteurs de démonstration créés."))
