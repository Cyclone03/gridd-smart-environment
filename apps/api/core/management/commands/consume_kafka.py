import os

from confluent_kafka import OFFSET_END
from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from core.kafka import (
    TOPIC_TO_TYPE,
    build_consumer,
    process_message,
)


def assign_partitions_at_live_edge(consumer, partitions):
    """Ignore committed backlog and consume only newly published messages."""
    for partition in partitions:
        partition.offset = OFFSET_END
    consumer.assign(partitions)


class Command(BaseCommand):
    help = (
        "Consomme les observations "
        "du Kafka réel du GRIDD"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--replay-backlog",
            action="store_true",
            help=(
                "Reprendre à la position Kafka enregistrée. À éviter pour le "
                "temps réel lorsque les messages n'ont pas d'horodatage."
            ),
        )

    def handle(
        self,
        *args,
        **options,
    ):
        kafka_enabled = os.getenv(
            "KAFKA_ENABLED",
            "false",
        ).lower()

        if kafka_enabled != "true":
            raise CommandError(
                "KAFKA_ENABLED=false"
            )

        self.stdout.write(
            "Initialisation du consumer Kafka..."
        )

        consumer = build_consumer()

        topics = list(
            TOPIC_TO_TYPE.keys()
        )

        self.stdout.write(
            "Topics configurés :"
        )

        for topic in topics:
            self.stdout.write(
                f"  - {topic}"
            )

        replay_backlog = options["replay_backlog"]
        if replay_backlog:
            consumer.subscribe(topics)
        else:
            consumer.subscribe(
                topics,
                on_assign=assign_partitions_at_live_edge,
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Consumer Kafka démarré."
            )
        )

        if replay_backlog:
            self.stdout.write(
                self.style.WARNING(
                    "Mode reprise du backlog activé."
                )
            )
        else:
            self.stdout.write(
                "Positionnement sur les nouvelles données (temps réel)."
            )

        self.stdout.write(
            "En attente des données GRIDD..."
        )

        try:
            while True:

                message = consumer.poll(
                    1.0,
                )

                if message is None:
                    continue

                if message.error():
                    self.stderr.write(
                        self.style.ERROR(
                            "Erreur Kafka: "
                            f"{message.error()}"
                        )
                    )

                    continue

                try:
                    _, kafka_timestamp_ms = message.timestamp()
                    observation = (
                        process_message(
                            message.topic(),
                            message.value(),
                            kafka_timestamp_ms=kafka_timestamp_ms,
                            kafka_partition=message.partition(),
                            kafka_offset=message.offset(),
                        )
                    )

                    # Commit uniquement après
                    # traitement réussi.
                    consumer.commit(
                        message=message,
                        asynchronous=False,
                    )

                    self.stdout.write(
                        self.style.SUCCESS(
                            (
                                f"{observation.zone.code}"
                                " | "
                                f"{observation.sensor.node_id}"
                                " | "
                                f"{observation.type}"
                                " | "
                                f"{observation.value}"
                                " "
                                f"{observation.unit}"
                                " | "
                                f"quality="
                                f"{observation.quality_status}"
                            )
                        )
                    )

                except Exception as exc:
                    self.stderr.write(
                        self.style.WARNING(
                            "Message rejeté: "
                            f"{exc}"
                        )
                    )

                    # On commit les messages invalides
                    # pour éviter de bloquer la partition.
                    consumer.commit(
                        message=message,
                        asynchronous=False,
                    )

        except KeyboardInterrupt:
            self.stdout.write(
                ""
            )

            self.stdout.write(
                self.style.WARNING(
                    "Arrêt demandé."
                )
            )

        finally:
            self.stdout.write(
                "Fermeture du consumer Kafka..."
            )

            consumer.close()

            self.stdout.write(
                self.style.SUCCESS(
                    "Consumer Kafka fermé."
                )
            )
