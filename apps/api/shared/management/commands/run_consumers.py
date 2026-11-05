import logging
import signal
import threading

from confluent_kafka import KafkaException
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from shared.contracts.topics import Topics
from shared.messaging import Messaging
from shared.messaging.subscription_registry import SubscriptionRegistry

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Démarre les consommateurs Kafka des modules : un thread et un consumer "
        "group par module. Sans --module, tous les modules sont démarrés."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--module",
            action="append",
            dest="modules",
            help="Module à démarrer (répétable) : ingestion, database, alarms, realtime.",
        )
        parser.add_argument(
            "--replay-backlog",
            action="store_true",
            help="Topics capteurs : reprendre à la position enregistrée au lieu des nouveaux messages.",
        )
        parser.add_argument("--list", action="store_true", help="Afficher les abonnements puis quitter.")

    def handle(self, *args, **options):
        registry = SubscriptionRegistry()
        try:
            subscriptions = registry.select(options["modules"])
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        for subscription in subscriptions:
            self.stdout.write(f"{subscription.name:<10} ← {', '.join(subscription.topics)}")
        if options["list"]:
            return

        if settings.EVENT_BUS != "kafka":
            raise CommandError(
                "EVENT_BUS=kafka requis. Avec le bus mémoire, les modules sont exécutés "
                "dans le processus qui publie (API, simulateur)."
            )

        messaging = Messaging.current()
        if settings.KAFKA_AUTO_CREATE_TOPICS:
            try:
                created = messaging.topic_provisioner().ensure(Topics.internal())
            except KafkaException as exc:
                raise CommandError(
                    f"Kafka injoignable ({settings.KAFKA_CONNECTIONS['main']['bootstrap_servers']}) : {exc}"
                ) from exc
            for topic in created:
                self.stdout.write(f"Topic créé : {topic}")

        stop_event = threading.Event()
        for signum in (signal.SIGINT, signal.SIGTERM):
            signal.signal(signum, lambda *_: stop_event.set())

        self.stdout.write(self.style.SUCCESS("Consommateurs démarrés. Ctrl+C pour arrêter."))
        messaging.consumer_runner().run(subscriptions, stop_event=stop_event, replay_backlog=options["replay_backlog"])
        self.stdout.write("Consommateurs arrêtés.")
