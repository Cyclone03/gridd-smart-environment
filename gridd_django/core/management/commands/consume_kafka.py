import os

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from core.kafka import (
    TOPIC_TO_TYPE,
    build_consumer,
    process_message,
)


class Command(BaseCommand):
    help = (
        "Consomme les observations "
        "du Kafka réel du GRIDD"
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

        consumer.subscribe(
            topics,
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Consumer Kafka démarré."
            )
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
                    observation = (
                        process_message(
                            message.topic(),
                            message.value(),
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