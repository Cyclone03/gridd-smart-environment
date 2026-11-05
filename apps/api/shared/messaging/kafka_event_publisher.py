import threading

from .event_publisher import EventPublisher
from .messaging_unavailable import MessagingUnavailable


class KafkaEventPublisher(EventPublisher):
    """Publication sur Kafka.

    Chaque publication attend l'accusé de réception du broker : un
    consommateur ne valide son offset qu'une fois ses propres messages
    réellement publiés (aucune perte entre deux modules).

    Le producteur n'est créé qu'à la première publication : un processus qui
    ne fait que lire (requête GET de l'API) n'a pas besoin de joindre Kafka.
    """

    def __init__(self, producer_factory, flush_timeout=10.0):
        self._producer_factory = producer_factory
        self._producer_instance = None
        self._lock = threading.Lock()
        self._flush_timeout = flush_timeout

    @property
    def _producer(self):
        with self._lock:
            if self._producer_instance is None:
                self._producer_instance = self._producer_factory()
        return self._producer_instance

    def publish_raw(self, topic, value, key=None):
        errors = []

        def on_delivery(error, _message):
            if error is not None:
                errors.append(error)

        try:
            self._producer.produce(topic, value=value, key=key, on_delivery=on_delivery)
        except BufferError as exc:
            raise MessagingUnavailable(f"File d'envoi Kafka pleine pour {topic}.") from exc
        remaining = self._producer.flush(self._flush_timeout)
        if remaining or errors:
            detail = errors[0] if errors else "délai dépassé"
            raise MessagingUnavailable(f"Publication impossible sur {topic} : {detail}")
