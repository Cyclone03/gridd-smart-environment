import json
import time

from django.core.management.base import BaseCommand

from core.kafka import (
    TOPIC_TO_TYPE,
    build_consumer,
)


class Command(BaseCommand):
    help = (
        "Inspecte les messages Kafka GRIDD "
        "sans les enregistrer en base."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--seconds",
            type=int,
            default=30,
            help="Durée d'écoute en secondes",
        )

    def handle(self, *args, **options):
        duration = options["seconds"]

        consumer = build_consumer()

        topics = list(
            TOPIC_TO_TYPE.keys()
        )

        self.stdout.write(
            "Inspection Kafka GRIDD"
        )

        self.stdout.write(
            "Topics écoutés :"
        )

        for topic in topics:
            self.stdout.write(
                f"  - {topic}"
            )

        consumer.subscribe(
            topics
        )

        counts = {
            topic: 0
            for topic in topics
        }

        nodes = {
            topic: set()
            for topic in topics
        }

        started_at = time.time()

        try:
            while (
                time.time() - started_at
                < duration
            ):
                message = consumer.poll(
                    1.0
                )

                if message is None:
                    continue

                if message.error():
                    self.stderr.write(
                        f"Kafka error: "
                        f"{message.error()}"
                    )
                    continue

                topic = message.topic()

                counts[topic] = (
                    counts.get(topic, 0)
                    + 1
                )

                try:
                    payload = json.loads(
                        message.value().decode(
                            "utf-8"
                        )
                    )

                except Exception as exc:
                    self.stderr.write(
                        f"{topic} | "
                        f"JSON invalide | "
                        f"{exc}"
                    )
                    continue

                node_id = (
                    payload.get("node_id")
                    or payload.get("nodeId")
                    or "unknown"
                )

                nodes.setdefault(
                    topic,
                    set(),
                ).add(
                    node_id
                )

                metadata = payload.get(
                    "metadata",
                    {},
                )

                zone = metadata.get(
                    "zone",
                    {},
                )

                zone_id = zone.get(
                    "id",
                    "unknown",
                )

                zone_label = zone.get(
                    "label",
                    "unknown",
                )

                self.stdout.write(
                    (
                        f"{topic}"
                        f" | node={node_id}"
                        f" | type={payload.get('type')}"
                        f" | value={payload.get('value')}"
                        f" | unit={payload.get('unit')}"
                        f" | zone={zone_id}"
                        f" ({zone_label})"
                    )
                )

        except KeyboardInterrupt:
            self.stdout.write(
                "Inspection interrompue."
            )

        finally:
            consumer.close()

        self.stdout.write("")
        self.stdout.write(
            "===== RÉSUMÉ ====="
        )

        for topic in topics:
            self.stdout.write(
                f"{topic}: "
                f"{counts.get(topic, 0)} messages"
            )

            topic_nodes = sorted(
                nodes.get(
                    topic,
                    set(),
                )
            )

            for node in topic_nodes:
                self.stdout.write(
                    f"    - {node}"
                )