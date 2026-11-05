import logging
import threading

from confluent_kafka import TopicPartition

from .inbound_message import InboundMessage
from .messaging_unavailable import MessagingUnavailable

logger = logging.getLogger(__name__)


class KafkaReplyListener:
    """Écoute du topic des réponses dans un processus émetteur de commandes.

    Toutes les partitions sont assignées manuellement à partir de leur fin
    actuelle, lue explicitement avant la première commande : aucun consumer
    group n'est créé, chaque processus voit toutes les réponses et aucune
    réponse publiée après le démarrage n'est manquée.
    """

    def __init__(self, consumer_factory, topic, handler):
        self._consumer_factory = consumer_factory
        self._topic = topic
        self._handler = handler
        self._lock = threading.Lock()
        self._thread = None

    def ensure_started(self):
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            consumer = self._consumer_factory()
            try:
                consumer.assign(self._current_end_offsets(consumer))
            except Exception as exc:
                consumer.close()
                raise MessagingUnavailable(f"Écoute des réponses impossible sur {self._topic} : {exc}") from exc
            self._thread = threading.Thread(target=self._loop, args=(consumer,), name="gridd-replies", daemon=True)
            self._thread.start()

    def _current_end_offsets(self, consumer):
        metadata = consumer.list_topics(self._topic, timeout=10).topics.get(self._topic)
        if metadata is None or metadata.error is not None or not metadata.partitions:
            raise MessagingUnavailable(f"Topic de réponses introuvable : {self._topic}")
        partitions = []
        for partition_id in metadata.partitions:
            _, high = consumer.get_watermark_offsets(TopicPartition(self._topic, partition_id), timeout=10)
            partitions.append(TopicPartition(self._topic, partition_id, high))
        return partitions

    def _loop(self, consumer):
        while True:
            message = consumer.poll(1.0)
            if message is None or message.error():
                continue
            try:
                self._handler.handle(InboundMessage(topic=message.topic(), value=message.value(), key=message.key()))
            except Exception:
                logger.exception("Réponse illisible sur %s.", self._topic)
