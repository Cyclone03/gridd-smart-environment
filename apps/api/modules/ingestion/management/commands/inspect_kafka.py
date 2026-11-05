import json
import time
from collections import Counter, defaultdict

from django.conf import settings
from django.core.management.base import BaseCommand

from shared.contracts.topics import Topics
from shared.messaging.kafka_client_factory import KafkaClientFactory
from shared.messaging.kafka_connection_config import KafkaConnectionConfig


class Command(BaseCommand):
    """Outil de diagnostic : affiche les messages capteurs sans rien publier ni enregistrer."""

    help = "Inspecte les messages des topics capteurs GRIDD sans les traiter."

    def add_arguments(self, parser):
        parser.add_argument("--seconds", type=int, default=30, help="Durée d'écoute en secondes")

    def handle(self, *args, **options):
        topics = list(Topics.sensors())
        factory = KafkaClientFactory(KafkaConnectionConfig.from_settings("sensors"))
        consumer = factory.consumer(f"{settings.KAFKA_CONSUMER_GROUP_PREFIX}.inspect", **{"auto.offset.reset": "latest"})
        consumer.subscribe(topics)
        self.stdout.write("Topics écoutés :\n" + "\n".join(f"  - {topic}" for topic in topics))

        counts, nodes = Counter(), defaultdict(set)
        deadline = time.time() + options["seconds"]
        try:
            while time.time() < deadline:
                message = consumer.poll(1.0)
                if message is None:
                    continue
                if message.error():
                    self.stderr.write(f"Erreur Kafka : {message.error()}")
                    continue
                counts[message.topic()] += 1
                self._show(message, nodes)
        except KeyboardInterrupt:
            self.stdout.write("Inspection interrompue.")
        finally:
            consumer.close()

        self.stdout.write("\n===== RÉSUMÉ =====")
        for topic in topics:
            self.stdout.write(f"{topic}: {counts[topic]} messages")
            for node in sorted(nodes[topic]):
                self.stdout.write(f"    - {node}")

    def _show(self, message, nodes):
        topic = message.topic()
        try:
            payload = json.loads(message.value().decode("utf-8"))
        except Exception as exc:
            self.stderr.write(f"{topic} | JSON invalide | {exc}")
            return
        node_id = payload.get("node_id") or payload.get("nodeId") or "unknown"
        nodes[topic].add(node_id)
        zone = (payload.get("metadata") or {}).get("zone") or {}
        self.stdout.write(
            f"{topic} | node={node_id} | type={payload.get('type')} | value={payload.get('value')} "
            f"| unit={payload.get('unit')} | zone={zone.get('id', 'unknown')} ({zone.get('label', 'unknown')})"
        )
