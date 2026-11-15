import logging
import time

from confluent_kafka import KafkaException, TopicPartition
from django.db import close_old_connections

from .inbound_message import InboundMessage
from .message_rejected import MessageRejected
from .messaging_unavailable import MessagingUnavailable
from .partition_assignment_monitor import PartitionAssignmentMonitor

logger = logging.getLogger(__name__)


class KafkaSubscriptionWorker:
    """Boucle de consommation d'un abonnement (un consumer Kafka, un thread).

    Traitement **par lots** : le premier message est attendu (``poll``), puis
    tous ceux déjà reçus par le client sont pris sans attendre (jusqu'à
    ``batch_size``). Un flux calme est donc traité message par message, sans
    latence ajoutée ; un arriéré est absorbé par lots.

    Livraison « au moins une fois » :

    1. chaque message du lot est traité ; ses publications partent sans
       attente (voir ``KafkaEventPublisher.begin_batch``) ;
    2. les accusés de réception de toutes ces publications sont attendus en
       une fois ;
    3. les offsets du lot sont validés en un seul appel.

    Si l'étape 2 échoue (broker indisponible), rien n'est validé : le lot est
    relu depuis son début après un délai (les modules sont idempotents).

    Par message :
    - ``MessageRejected`` : journalisé puis ignoré (il ne deviendra jamais valide) ;
    - autre erreur : nouvelles tentatives jusqu'à ``max_attempts``, puis
      abandon journalisé pour ne pas bloquer la partition.

    Le gestionnaire peut définir ``begin_batch()`` / ``end_batch()`` pour
    regrouper son propre travail (ex. une seule diffusion par lot).
    """

    POLL_TIMEOUT_SECONDS = 1.0

    def __init__(
        self,
        subscription,
        consumer,
        *,
        stop_event,
        live_edge,
        max_attempts,
        retry_delay,
        publishers=(),
        batch_size=500,
        sleep=time.sleep,
    ):
        self._subscription = subscription
        self._consumer = consumer
        self._stop_event = stop_event
        self._live_edge = live_edge
        self._max_attempts = max(1, max_attempts)
        self._retry_delay = retry_delay
        self._publishers = tuple(publishers)
        self._batch_size = max(1, batch_size)
        self._sleep = sleep
        self._handler = None
        # Dernier passage dans la boucle (surveillé par KafkaConsumerRunner).
        self.last_progress = time.monotonic()

    def run(self):
        name = self._subscription.name
        topics = list(self._subscription.topics)
        # Attributions journalisées ; partitions lues par un autre membre signalées.
        monitor = PartitionAssignmentMonitor(name, topics, live_edge=self._live_edge)
        self._consumer.subscribe(topics, on_assign=monitor.on_assign, on_revoke=monitor.on_revoke)
        logger.info("[%s] abonné à %s%s", name, ", ".join(topics), " (temps réel)" if self._live_edge else "")
        try:
            self._handler = self._subscription.handler_factory()
            while not self._stop_event.is_set():
                self.last_progress = time.monotonic()
                first = self._consumer.poll(self.POLL_TIMEOUT_SECONDS)
                monitor.check(self._consumer)
                if first is None:
                    continue
                batch = [first]
                if self._batch_size > 1:
                    batch.extend(self._consumer.consume(num_messages=self._batch_size - 1, timeout=0))
                self.process_batch(batch)
        except Exception:
            logger.exception("[%s] arrêt inattendu du consommateur.", name)
            raise
        finally:
            self._consumer.close()
            logger.info("[%s] consommateur fermé.", name)

    def process(self, message):
        """Traite un message isolé (lot d'un seul message)."""
        self.process_batch([message])

    def process_batch(self, messages):
        valid = []
        for message in messages:
            if message.error():
                logger.error("[%s] erreur Kafka : %s", self._subscription.name, message.error())
            else:
                valid.append(message)
        if not valid:
            return

        for publisher in self._publishers:
            publisher.begin_batch()
        try:
            self._call_handler_hook("begin_batch")
            for message in valid:
                self._handle(message)
            self._call_handler_hook("end_batch")
            for publisher in self._publishers:
                publisher.end_batch()
        except MessagingUnavailable as exc:
            self._rewind(valid, exc)
            return
        finally:
            for publisher in self._publishers:
                publisher.discard_batch()
        self._commit(valid)

    def _handle(self, message):
        inbound = self._to_inbound(message)
        attempt = 1
        while True:
            close_old_connections()
            try:
                self._handler.handle(inbound)
                return
            except MessageRejected as exc:
                logger.warning("[%s] message rejeté (%s@%s) : %s", self._subscription.name, inbound.topic, inbound.offset, exc)
                return
            except Exception:
                if attempt >= self._max_attempts or self._stop_event.is_set():
                    logger.exception(
                        "[%s] message abandonné après %s tentative(s) (%s@%s).",
                        self._subscription.name,
                        attempt,
                        inbound.topic,
                        inbound.offset,
                    )
                    return
                logger.exception(
                    "[%s] échec, nouvelle tentative %s/%s.", self._subscription.name, attempt + 1, self._max_attempts
                )
                self._sleep(self._retry_delay * attempt)
                attempt += 1

    def _call_handler_hook(self, name):
        hook = getattr(self._handler, name, None)
        if callable(hook):
            hook()

    def _commit(self, messages):
        last = {}
        for message in messages:
            key = (message.topic(), message.partition())
            last[key] = max(last.get(key, -1), message.offset())
        offsets = [TopicPartition(topic, partition, offset + 1) for (topic, partition), offset in last.items()]
        try:
            self._consumer.commit(offsets=offsets, asynchronous=False)
        except KafkaException as exc:
            # Partition retirée pendant le lot (rééquilibrage) : le nouveau
            # propriétaire relira ces messages ; les modules sont idempotents.
            logger.warning("[%s] validation des offsets impossible : %s", self._subscription.name, exc)

    def _rewind(self, messages, error):
        first = {}
        for message in messages:
            key = (message.topic(), message.partition())
            first[key] = min(first.get(key, message.offset()), message.offset())
        logger.error(
            "[%s] publications non confirmées (%s) : relecture de %s message(s).",
            self._subscription.name,
            error,
            len(messages),
        )
        for (topic, partition), offset in first.items():
            try:
                self._consumer.seek(TopicPartition(topic, partition, offset))
            except KafkaException:
                logger.warning("[%s] retour en arrière impossible sur %s[%s].", self._subscription.name, topic, partition)
        # État local (caches) peut-être en avance sur ce qui a été publié : repartir de la base.
        self._handler = self._subscription.handler_factory()
        self._sleep(self._retry_delay)

    @staticmethod
    def _to_inbound(message):
        _, timestamp_ms = message.timestamp()
        return InboundMessage(
            topic=message.topic(),
            value=message.value(),
            key=message.key(),
            partition=message.partition(),
            offset=message.offset(),
            timestamp_ms=timestamp_ms if timestamp_ms is not None and timestamp_ms >= 0 else None,
        )
