from confluent_kafka import Consumer, Producer
from confluent_kafka.admin import AdminClient
from django.conf import settings

from .kafka_connection_config import KafkaConnectionConfig


class KafkaClientFactory:
    """Construit les clients confluent-kafka d'une connexion."""

    def __init__(self, config: KafkaConnectionConfig, prefetch_messages=None):
        self._config = config
        if prefetch_messages is None:
            prefetch_messages = getattr(settings, "KAFKA_PREFETCH_MESSAGES", 1000)
        self._prefetch_messages = prefetch_messages

    @property
    def config(self) -> KafkaConnectionConfig:
        return self._config

    def producer(self) -> Producer:
        return Producer({**self._config.client_config(), "acks": "all", "enable.idempotence": True})

    def consumer(self, group_id, **overrides) -> Consumer:
        options = {
            **self._config.client_config(),
            "group.id": group_id,
            # Validation manuelle après traitement : livraison au moins une fois.
            "enable.auto.commit": False,
            # Un module qui démarre lit tout ce qui lui a été destiné.
            "auto.offset.reset": "earliest",
            # Préchargement par partition (défaut librdkafka : 100 000 messages).
            # Pendant le rattrapage d'une partition, les messages récents des
            # autres partitions attendaient derrière tout ce préchargement : les
            # zones à jour prenaient elles aussi des dizaines de minutes de retard.
            "queued.min.messages": self._prefetch_messages,
        }
        options.update(overrides)
        return Consumer(options)

    def admin(self) -> AdminClient:
        return AdminClient(self._config.client_config())
