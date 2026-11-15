import logging
from collections import defaultdict

from confluent_kafka import OFFSET_END

logger = logging.getLogger(__name__)


class PartitionAssignmentMonitor:
    """Callbacks de rééquilibrage d'un consumer : journalise les partitions
    attribuées / retirées et signale celles lues par un autre membre du groupe.

    Pourquoi : si une autre instance du backend (autre poste, ancienne version,
    deuxième ``docker compose``…) rejoint le même consumer group, Kafka lui
    confie une partie des partitions. Les messages de ces partitions (donc
    des zones correspondantes) partent alors vers cette autre instance et
    n'arrivent plus dans cette base, sans aucune erreur. Ce moniteur rend la
    situation visible dans les journaux.

    La vérification du nombre total de partitions (requête de métadonnées) est
    faite hors du callback, par ``check()`` appelé depuis la boucle de lecture.
    """

    METADATA_TIMEOUT_SECONDS = 5.0

    def __init__(self, name, topics, *, live_edge=False):
        self._name = name
        self._topics = tuple(topics)
        self._live_edge = live_edge
        self._assigned = set()
        self._pending_check = False

    def on_assign(self, consumer, partitions):
        if self._live_edge:
            # Temps réel capteurs : ignorer l'arriéré validé.
            for partition in partitions:
                partition.offset = OFFSET_END
        consumer.assign(partitions)
        self._assigned = {(partition.topic, partition.partition) for partition in partitions}
        self._pending_check = True
        logger.info("[%s] partitions attribuées : %s", self._name, self.describe(self._assigned) or "aucune")

    def on_revoke(self, consumer, partitions):
        logger.info(
            "[%s] partitions retirées : %s",
            self._name,
            self.describe({(partition.topic, partition.partition) for partition in partitions}) or "aucune",
        )
        self._assigned = set()

    def check(self, consumer):
        """Compare l'attribution aux partitions existantes (une fois par rééquilibrage)."""
        if not self._pending_check:
            return
        self._pending_check = False
        missing = {}
        for topic in sorted(set(self._topics) | {topic for topic, _ in self._assigned}):
            try:
                metadata = consumer.list_topics(topic, timeout=self.METADATA_TIMEOUT_SECONDS).topics.get(topic)
            except Exception:
                logger.debug("[%s] métadonnées indisponibles pour %s.", self._name, topic, exc_info=True)
                continue
            if metadata is None or metadata.error is not None:
                continue
            absent = sorted(set(metadata.partitions) - {p for t, p in self._assigned if t == topic})
            if absent:
                missing[topic] = absent
        if missing:
            detail = "; ".join(f"{topic} {self._format(parts)}" for topic, parts in missing.items())
            logger.warning(
                "[%s] partitions lues par un AUTRE membre du consumer group : %s. Les messages de ces "
                "partitions ne seront pas traités par cette instance (pour l'ingestion/la base : les zones "
                "concernées n'apparaîtront pas). Si une seule instance est prévue, une autre instance utilise "
                "le même KAFKA_CONSUMER_GROUP_PREFIX : vérifier avec `python manage.py kafka_groups`.",
                self._name,
                detail,
            )

    @classmethod
    def describe(cls, assigned):
        by_topic = defaultdict(list)
        for topic, partition in assigned:
            by_topic[topic].append(partition)
        return ", ".join(f"{topic} {cls._format(sorted(parts))}" for topic, parts in sorted(by_topic.items()))

    @staticmethod
    def _format(partitions):
        return "[" + ", ".join(f"p{partition}" for partition in partitions) + "]"
