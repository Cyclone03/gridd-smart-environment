from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from modules.ingestion.adapters.messaging.sensor_topic_replayer import SensorTopicReplayer
from modules.ingestion.composition import sensor_reading_consumer
from shared.contracts.topics import Topics
from shared.messaging import Messaging, MessagingUnavailable
from shared.messaging.kafka_client_factory import KafkaClientFactory
from shared.messaging.kafka_connection_config import KafkaConnectionConfig


class Command(BaseCommand):
    help = (
        "Relit les topics capteurs GRIDD entre deux instants et retraite les mesures. "
        "Idempotent : les mesures déjà enregistrées sont ignorées, seules les manquantes sont ajoutées."
    )

    def add_arguments(self, parser):
        parser.add_argument("--since", required=True, help="Début (ISO 8601, ex. 2026-11-24T15:00:00-05:00)")
        parser.add_argument("--until", help="Fin (ISO 8601) ; défaut : maintenant")
        parser.add_argument("--topic", action="append", help="Topic capteur à relire (répétable) ; défaut : tous")
        parser.add_argument("--dry-run", action="store_true", help="Affiche seulement le nombre de messages à relire.")

    def handle(self, *args, **options):
        since = self._instant(options["since"], "--since")
        until = self._instant(options["until"], "--until") if options["until"] else timezone.now()
        if until <= since:
            raise CommandError("--until doit être postérieur à --since.")
        topics = options["topic"] or list(Topics.sensors())
        unknown = sorted(set(topics) - set(Topics.sensors()))
        if unknown:
            raise CommandError(f"Topics capteurs inconnus : {', '.join(unknown)}")
        if not options["dry_run"] and not Messaging.current().is_kafka:
            self.stdout.write(self.style.WARNING("EVENT_BUS=memory : les mesures sont traitées dans ce processus."))

        factory = KafkaClientFactory(KafkaConnectionConfig.from_settings("sensors"))
        # Partitions assignées directement, aucun offset validé : le groupe
        # temps réel de l'ingestion n'est pas modifié.
        consumer = factory.consumer(f"{settings.KAFKA_CONSUMER_GROUP_PREFIX}.ingestion-replay")
        replayer = SensorTopicReplayer(
            consumer,
            sensor_reading_consumer(),
            Messaging.current().publisher(),
            batch_size=settings.KAFKA_BATCH_SIZE,
            on_batch=close_old_connections,
        )
        try:
            plan = replayer.plan(topics, since_ms=self._ms(since))
            total = sum(end - first for first, end in plan.values())
            self.stdout.write(f"Période : {since.isoformat()} → {until.isoformat()}")
            for (topic, partition), (first, end) in sorted(plan.items()):
                self.stdout.write(f"  {topic}[{partition}] : offsets {first} → {end - 1} ({end - first} messages max)")
            self.stdout.write(f"Au plus {total} messages à relire (limités ensuite par --until).")
            if options["dry_run"] or not plan:
                return
            report = replayer.replay(plan, until_ms=self._ms(until))
        except MessagingUnavailable as exc:
            raise CommandError(f"Publication impossible, rejeu interrompu (relancer sans risque) : {exc}") from exc
        finally:
            consumer.close()

        self.stdout.write(
            self.style.SUCCESS(
                f"Rejeu terminé : {report.read} lus, {report.accepted} acceptés (déjà présents ignorés par la base), "
                f"{report.rejected} rejetés."
            )
        )
        for reason, count in report.reasons.most_common(10):
            self.stdout.write(f"  rejet « {reason} » : {count}")

    @staticmethod
    def _instant(raw, label) -> datetime:
        value = parse_datetime(raw)
        if value is None:
            raise CommandError(f"{label} doit être une date et heure ISO 8601.")
        return timezone.make_aware(value) if timezone.is_naive(value) else value

    @staticmethod
    def _ms(value) -> int:
        return int(value.timestamp() * 1000)
