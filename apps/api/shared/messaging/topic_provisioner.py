import logging

from confluent_kafka import KafkaError, KafkaException
from confluent_kafka.admin import NewTopic

logger = logging.getLogger(__name__)


class TopicProvisioner:
    """Crée les topics internes manquants (``KAFKA_AUTO_CREATE_TOPICS``)."""

    def __init__(self, admin, *, partitions, replication_factor):
        self._admin = admin
        self._partitions = partitions
        self._replication_factor = replication_factor

    def ensure(self, topics):
        existing = set(self._admin.list_topics(timeout=10).topics)
        missing = [topic for topic in dict.fromkeys(topics) if topic not in existing]
        if not missing:
            return []
        futures = self._admin.create_topics(
            [NewTopic(topic, num_partitions=self._partitions, replication_factor=self._replication_factor) for topic in missing]
        )
        for topic, future in futures.items():
            try:
                future.result()
                logger.info("Topic créé : %s", topic)
            except KafkaException as exc:
                if exc.args[0].code() != KafkaError.TOPIC_ALREADY_EXISTS:
                    raise
        return missing
