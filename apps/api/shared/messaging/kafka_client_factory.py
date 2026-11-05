from confluent_kafka import Consumer, Producer
from confluent_kafka.admin import AdminClient

from .kafka_connection_config import KafkaConnectionConfig


class KafkaClientFactory:
    """Construit les clients confluent-kafka d'une connexion."""

    def __init__(self, config: KafkaConnectionConfig):
        self._config = config

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
        }
        options.update(overrides)
        return Consumer(options)

    def admin(self) -> AdminClient:
        return AdminClient(self._config.client_config())
