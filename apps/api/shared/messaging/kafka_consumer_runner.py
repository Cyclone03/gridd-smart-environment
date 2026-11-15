import logging
import os
import socket
import threading
import time
from pathlib import Path

from .kafka_subscription_worker import KafkaSubscriptionWorker

logger = logging.getLogger(__name__)


class KafkaConsumerRunner:
    """Exécute les abonnements des modules : un thread et un consumer group
    par module (``<préfixe>.<module>``), jusqu'à la demande d'arrêt.

    Surveillance :
    - tant que tous les modules avancent, ``heartbeat_file`` est mis à jour
      (healthcheck Docker du service ``kafka-consumer``) ;
    - un module dont la boucle est bloquée depuis ``stall_seconds`` arrête le
      processus : Docker le redémarre, au lieu de laisser un module muet des
      heures sans aucune erreur visible.
    """

    HEARTBEAT_INTERVAL_SECONDS = 10.0
    STALL_EXIT_CODE = 70

    def __init__(
        self,
        client_factories,
        *,
        group_prefix,
        max_attempts,
        retry_delay,
        publishers=(),
        batch_size=500,
        stall_seconds=300.0,
        heartbeat_file=None,
        clock=time.monotonic,
        exit=os._exit,
    ):
        self._client_factories = client_factories
        self._group_prefix = group_prefix
        self._max_attempts = max_attempts
        self._retry_delay = retry_delay
        # Publishers utilisés par les modules : leurs envois sont confirmés une
        # fois par lot, avant la validation des offsets.
        self._publishers = tuple(publishers)
        self._batch_size = batch_size
        self._stall_seconds = stall_seconds
        self._heartbeat_file = Path(heartbeat_file) if heartbeat_file else None
        self._clock = clock
        self._exit = exit
        self._last_heartbeat = None

    def run(self, subscriptions, *, stop_event, replay_backlog=False):
        threads, workers = [], []
        for subscription in subscriptions:
            factory = self._client_factories[subscription.connection]
            group = f"{self._group_prefix}.{subscription.name}"
            # Identifie chaque instance dans `kafka_groups` et les outils Kafka.
            client_id = f"{group}@{socket.gethostname()}:{os.getpid()}"
            worker = KafkaSubscriptionWorker(
                subscription,
                factory.consumer(group, **{"client.id": client_id}),
                stop_event=stop_event,
                live_edge=subscription.start_at_live_edge and not replay_backlog,
                max_attempts=self._max_attempts,
                retry_delay=self._retry_delay,
                publishers=self._publishers,
                batch_size=self._batch_size,
            )
            thread = threading.Thread(target=self._guard, args=(worker, stop_event), name=f"gridd-{subscription.name}")
            thread.start()
            threads.append(thread)
            workers.append((subscription.name, worker))

        while any(thread.is_alive() for thread in threads):
            for thread in threads:
                thread.join(timeout=0.5)
            if not stop_event.is_set():
                self.watch(workers)

    def watch(self, workers):
        """Battement de cœur si tous les modules avancent ; arrêt du processus sinon."""
        now = self._clock()
        stalled = [name for name, worker in workers if now - worker.last_progress > self._stall_seconds]
        if stalled:
            logger.critical(
                "Module(s) bloqué(s) depuis plus de %ss : %s. Arrêt du processus pour redémarrage.",
                int(self._stall_seconds),
                ", ".join(stalled),
            )
            logging.shutdown()
            self._exit(self.STALL_EXIT_CODE)
            return
        if self._heartbeat_file and (
            self._last_heartbeat is None or now - self._last_heartbeat >= self.HEARTBEAT_INTERVAL_SECONDS
        ):
            try:
                self._heartbeat_file.touch()
                self._last_heartbeat = now
            except OSError:
                logger.warning("Battement de cœur impossible : %s", self._heartbeat_file)

    @staticmethod
    def _guard(worker, stop_event):
        try:
            worker.run()
        except Exception:
            # Un module en panne arrête le processus entier : l'orchestrateur
            # (Docker, systemd) le redémarre plutôt que de laisser un module muet.
            stop_event.set()
