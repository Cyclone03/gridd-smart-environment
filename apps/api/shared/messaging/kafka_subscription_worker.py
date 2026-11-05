import logging
import time

from django.db import close_old_connections

from .inbound_message import InboundMessage
from .live_edge_assigner import LiveEdgeAssigner
from .message_rejected import MessageRejected

logger = logging.getLogger(__name__)


class KafkaSubscriptionWorker:
    """Boucle de consommation d'un abonnement (un consumer Kafka, un thread).

    Livraison « au moins une fois » : l'offset n'est validé qu'après le
    traitement du message.

    - ``MessageRejected`` : message journalisé puis validé (il ne deviendra
      jamais valide) ;
    - autre erreur : nouvelle tentative du même message, jusqu'à
      ``max_attempts``, puis abandon journalisé pour ne pas bloquer la partition.
    """

    POLL_TIMEOUT_SECONDS = 1.0

    def __init__(self, subscription, consumer, *, stop_event, live_edge, max_attempts, retry_delay, sleep=time.sleep):
        self._subscription = subscription
        self._consumer = consumer
        self._stop_event = stop_event
        self._live_edge = live_edge
        self._max_attempts = max(1, max_attempts)
        self._retry_delay = retry_delay
        self._sleep = sleep
        self._handler = None

    def run(self):
        name = self._subscription.name
        topics = list(self._subscription.topics)
        if self._live_edge:
            self._consumer.subscribe(topics, on_assign=LiveEdgeAssigner())
        else:
            self._consumer.subscribe(topics)
        logger.info("[%s] abonné à %s%s", name, ", ".join(topics), " (temps réel)" if self._live_edge else "")
        try:
            self._handler = self._subscription.handler_factory()
            while not self._stop_event.is_set():
                message = self._consumer.poll(self.POLL_TIMEOUT_SECONDS)
                if message is None:
                    continue
                if message.error():
                    logger.error("[%s] erreur Kafka : %s", name, message.error())
                    continue
                self.process(message)
        except Exception:
            logger.exception("[%s] arrêt inattendu du consommateur.", name)
            raise
        finally:
            self._consumer.close()
            logger.info("[%s] consommateur fermé.", name)

    def process(self, message):
        inbound = self._to_inbound(message)
        attempt = 1
        while True:
            close_old_connections()
            try:
                self._handler.handle(inbound)
                break
            except MessageRejected as exc:
                logger.warning("[%s] message rejeté (%s@%s) : %s", self._subscription.name, inbound.topic, inbound.offset, exc)
                break
            except Exception:
                if attempt >= self._max_attempts or self._stop_event.is_set():
                    logger.exception(
                        "[%s] message abandonné après %s tentative(s) (%s@%s).",
                        self._subscription.name,
                        attempt,
                        inbound.topic,
                        inbound.offset,
                    )
                    break
                logger.exception(
                    "[%s] échec, nouvelle tentative %s/%s.", self._subscription.name, attempt + 1, self._max_attempts
                )
                self._sleep(self._retry_delay * attempt)
                attempt += 1
        self._consumer.commit(message=message, asynchronous=False)

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
