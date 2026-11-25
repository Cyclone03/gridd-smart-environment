from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from modules.database.adapters.messaging.database_events_producer import DatabaseEventsProducer
from modules.database.models import (
    AlarmRule,
    AlarmRuleState,
    Alert,
    ClimatePrediction,
    ComfortAssessment,
    EnergyEstimate,
    Observation,
    Sensor,
    Zone,
)
from shared.kernel.metrics import MetricCatalog
from shared.kernel.sensor_identity import sensor_key
from shared.kernel.vocabulary import AlertResolution
from shared.messaging import Messaging


class Command(BaseCommand):
    help = (
        "Fusionne un espace créé par erreur (ex. « node01 ») dans un espace existant : "
        "mesures, capteurs, alertes et règles sont rattachés à l'espace cible, puis l'espace source est supprimé."
    )

    def add_arguments(self, parser):
        parser.add_argument("source", help="Code de l'espace à fusionner (ex. node01)")
        parser.add_argument("target", help="Code de l'espace cible (ex. individual-work-cubicle-01)")
        parser.add_argument("--dry-run", action="store_true", help="Affiche ce qui serait déplacé, sans rien modifier.")

    def handle(self, *args, **options):
        source = Zone.objects.filter(code=options["source"]).first()
        target = Zone.objects.filter(code=options["target"]).first()
        if source is None or target is None:
            missing = options["source"] if source is None else options["target"]
            raise CommandError(f"Espace introuvable : {missing}")
        if source.pk == target.pk:
            raise CommandError("La source et la cible sont le même espace.")

        with transaction.atomic():
            summary = self._merge(source, target)
            if options["dry_run"]:
                transaction.set_rollback(True)

        for label, count in summary.items():
            self.stdout.write(f"  {label} : {count}")
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Simulation : aucune modification enregistrée."))
            return
        events = DatabaseEventsProducer(Messaging.current().publisher())
        events.zones_changed(target.code)
        events.alerts_changed(target.code)
        self.stdout.write(self.style.SUCCESS(f"« {options['source']} » fusionné dans « {target.code} »."))

    @staticmethod
    def _merge(source, target):
        summary = {"capteurs": 0, "mesures": 0, "alertes": 0, "règles": 0}
        for sensor in list(Sensor.objects.filter(zone=source)):
            metadata = dict(sensor.metadata) if isinstance(sensor.metadata, dict) else {}
            metadata.setdefault("source_node_id", sensor.node_id)
            definition = MetricCatalog.get(sensor.sensor_type)
            canonical, _ = Sensor.objects.get_or_create(
                node_id=sensor_key(target.code, sensor.sensor_type),
                sensor_type=sensor.sensor_type,
                defaults={
                    "label": f"{target.name} — {definition.label if definition else sensor.sensor_type}",
                    "zone": target,
                    "unit": sensor.unit,
                    "metadata": metadata,
                    "active": sensor.active,
                },
            )
            if sensor.active and not canonical.active:
                canonical.active = True
                canonical.save(update_fields=["active"])
            summary["mesures"] += Observation.objects.filter(sensor=sensor).update(sensor=canonical, zone=target)
            sensor.delete()
            summary["capteurs"] += 1
        summary["mesures"] += Observation.objects.filter(zone=source).update(zone=target)

        # Une seule alerte active par espace et par code : celles de la source
        # déjà présentes dans la cible sont clôturées.
        target_codes = set(Alert.objects.filter(zone=target, active=True).values_list("code", flat=True))
        Alert.objects.filter(zone=source, active=True, code__in=target_codes).update(
            active=False, resolved_at=timezone.now(), resolution=AlertResolution.MIGRATED
        )
        summary["alertes"] = Alert.objects.filter(zone=source).update(zone=target)
        summary["règles"] = AlarmRule.objects.filter(zone=source).update(zone=target)
        AlarmRuleState.objects.filter(zone=source).delete()
        for model in (ClimatePrediction, ComfortAssessment, EnergyEstimate):
            model.objects.filter(zone=source).update(zone=target)
        source.delete()
        return summary
