from django.core.management.base import BaseCommand
from core.models import AlarmRule, Sensor, ThresholdProfile, Zone


# Règles de démonstration créées seulement si aucune règle n'existe.
# Valeurs illustratives : à adapter au contexte (voir docs/alarms.md).
DEMO_RULES = [
    dict(name="Température hors plage", metric="temperature", operator="outside_range",
         threshold=18, threshold_high=28, severity="warning", hysteresis=0.5),
    dict(name="Humidité hors plage", metric="humidity", operator="outside_range",
         threshold=30, threshold_high=60, severity="warning", hysteresis=2),
    dict(name="Niveau sonore élevé", metric="sound_level", operator="gt",
         threshold=70, severity="warning", min_duration_seconds=60, hysteresis=3),
    dict(name="Capacité dépassée", metric="occupancy", operator="gt",
         threshold=30, severity="critical"),
]


class Command(BaseCommand):
    help = "Crée des zones et capteurs de démonstration"

    def handle(self, *args, **options):
        zones = [
            ("Bureau des professeurs", "professors-office", Zone.ZoneType.OFFICE),
            ("Cubicule de travail individuel 01", "individual-work-cubicle-01", Zone.ZoneType.CUBICLE),
            ("Cubicule de travail individuel 02", "individual-work-cubicle-02", Zone.ZoneType.CUBICLE),
            ("Espace de travail ouvert", "open-workspace", Zone.ZoneType.OPEN_WORKSPACE),
            ("Salle de réunion", "meeting-room", Zone.ZoneType.MEETING_ROOM),
            ("Salle des serveurs et équipements", "server-equipment-room", Zone.ZoneType.SERVER_ROOM),
        ]

        for name, code, zone_type in zones:
            zone, _ = Zone.objects.get_or_create(
                code=code,
                defaults={"name": name, "zone_type": zone_type},
            )
            profile, _ = ThresholdProfile.objects.get_or_create(zone=zone)
            if not profile.enabled:
                profile.enabled = True
                profile.save(update_fields=["enabled"])

            sensor_defs = [
                ("temperature", "°C"),
                ("humidity", "%"),
                ("co2", "ppm"),
                ("sound_level", "dBA"),
                ("occupancy", "count"),
            ]
            for sensor_type, unit in sensor_defs:
                demo_node_id = f"{code}-{sensor_type}"
                real_sensor_exists = zone.sensors.filter(
                    sensor_type=sensor_type,
                    active=True,
                ).exclude(node_id=demo_node_id).exists()
                if real_sensor_exists:
                    Sensor.objects.filter(
                        node_id=demo_node_id,
                        sensor_type=sensor_type,
                    ).update(active=False)
                    continue

                sensor, _ = Sensor.objects.get_or_create(
                    node_id=demo_node_id,
                    sensor_type=sensor_type,
                    defaults={
                        "label": f"{name} — {sensor_type}",
                        "zone": zone,
                        "unit": unit,
                    },
                )
                if not sensor.active:
                    sensor.active = True
                    sensor.save(update_fields=["active"])

        if not AlarmRule.objects.exists():
            for rule in DEMO_RULES:
                AlarmRule.objects.create(
                    description="Règle de démonstration créée par seed_gridd.",
                    **rule,
                )
            self.stdout.write("Règles d'alarme de démonstration créées.")

        self.stdout.write(self.style.SUCCESS("Zones et capteurs de démonstration créés."))
