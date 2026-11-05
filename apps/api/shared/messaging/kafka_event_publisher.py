from .event_publisher import EventPublisher
from .messaging_unavailable import MessagingUnavailable


class KafkaEventPublisher(EventPublisher):
    """Publication sur Kafka.

    Chaque publication attend l'accusé de réception du broker : un
    consommateur ne valide son offset qu'une fois ses propres messages
    réellement publiés (aucune perte entre deux modules).
    """

    def __init__(self, producer, flush_timeout=10.0):
        self._producer = producer
        self._flush_timeout = flush_timeout

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
