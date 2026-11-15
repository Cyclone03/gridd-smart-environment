from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from shared.messaging.consumer_group_inspector import ConsumerGroupInspector
from shared.messaging.kafka_client_factory import KafkaClientFactory
from shared.messaging.kafka_connection_config import KafkaConnectionConfig
from shared.messaging.subscription_registry import SubscriptionRegistry


class Command(BaseCommand):
    """Diagnostic : qui lit quoi dans les consumer groups des modules.

    Symptôme typique : les données de certaines zones n'arrivent plus en base
    alors que d'autres continuent. Les messages internes sont répartis par
    zone sur les partitions ; si une autre instance du backend partage le
    même consumer group, elle reçoit une partie des partitions — et donc des
    zones — sans qu'aucune erreur n'apparaisse ici.
    """

    help = "Affiche les membres, partitions et retards des consumer groups GRIDD."

    def add_arguments(self, parser):
        parser.add_argument("--module", action="append", dest="modules", help="Module à inspecter (répétable).")

    def handle(self, *args, **options):
        if settings.EVENT_BUS != "kafka":
            raise CommandError("EVENT_BUS=kafka requis.")
        try:
            subscriptions = SubscriptionRegistry().select(options["modules"])
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        problems = 0
        for subscription in subscriptions:
            group = f"{settings.KAFKA_CONSUMER_GROUP_PREFIX}.{subscription.name}"
            admin = KafkaClientFactory(KafkaConnectionConfig.from_settings(subscription.connection)).admin()
            try:
                status = ConsumerGroupInspector(admin).inspect(group, subscription.topics)
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"{group} : inspection impossible ({exc})"))
                problems += 1
                continue
            problems += self._show(status)

        if problems:
            self.stdout.write(
                self.style.WARNING(
                    "\nSi une seule instance du backend doit tourner : arrêter l'autre instance, ou lui donner "
                    "un KAFKA_CONSUMER_GROUP_PREFIX différent (voir docs/deployment.md, "
                    "« Données d’une partie des espaces absentes »)."
                )
            )

    def _show(self, status) -> int:
        problems = 0
        heading = f"\n{status.group}  (état : {status.state}, {len(status.members)} membre(s))"
        self.stdout.write(self.style.MIGRATE_HEADING(heading))
        for label, assigned in status.members:
            parts = ", ".join(f"{topic}[p{number}]" for topic, number in assigned) or "aucune partition"
            self.stdout.write(f"  membre  {label} → {parts}")
        if len(status.members) > 1:
            problems += 1
            self.stdout.write(
                self.style.WARNING(
                    "  ⚠ plusieurs membres : les partitions (et donc les zones) sont réparties entre eux. "
                    "Chaque membre n'écrit que dans sa propre base."
                )
            )
        for item in status.partitions:
            lag = "?" if item.lag is None else str(item.lag)
            line = (
                f"  {item.topic} p{item.partition}  validé={item.committed if item.committed is not None else '-'}  "
                f"fin={item.end if item.end is not None else '?'}  retard={lag}  lu par={item.owner or 'personne'}"
            )
            if item.owner is None and item.lag:
                problems += 1
                self.stdout.write(self.style.WARNING(line + "  ⚠ non consommée"))
            else:
                self.stdout.write(line)
        return problems
