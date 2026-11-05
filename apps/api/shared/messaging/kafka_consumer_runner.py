import logging
import threading

from .kafka_subscription_worker import KafkaSubscriptionWorker

logger = logging.getLogger(__name__)


class KafkaConsumerRunner:
    """Exécute les abonnements des modules : un thread et un consumer group
    par module (``<préfixe>.<module>``), jusqu'à la demande d'arrêt."""

    def __init__(self, client_factories, *, group_prefix, max_attempts, retry_delay):
        self._client_factories = client_factories
        self._group_prefix = group_prefix
        self._max_attempts = max_attempts
        self._retry_delay = retry_delay

    def run(self, subscriptions, *, stop_event, replay_backlog=False):
        threads = []
        for subscription in subscriptions:
            factory = self._client_factories[subscription.connection]
            worker = KafkaSubscriptionWorker(
                subscription,
                factory.consumer(f"{self._group_prefix}.{subscription.name}"),
                stop_event=stop_event,
                live_edge=subscription.start_at_live_edge and not replay_backlog,
                max_attempts=self._max_attempts,
                retry_delay=self._retry_delay,
            )
            thread = threading.Thread(target=self._guard, args=(worker, stop_event), name=f"gridd-{subscription.name}")
            thread.start()
            threads.append(thread)

        while any(thread.is_alive() for thread in threads):
            for thread in threads:
                thread.join(timeout=0.5)

    @staticmethod
    def _guard(worker, stop_event):
        try:
            worker.run()
        except Exception:
            # Un module en panne arrête le processus entier : l'orchestrateur
            # (Docker, systemd) le redémarre plutôt que de laisser un module muet.
            stop_event.set()
