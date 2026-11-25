import logging

from confluent_kafka import TopicPartition

from shared.messaging import InboundMessage, MessageRejected

from .replay_report import ReplayReport

logger = logging.getLogger(__name__)


class SensorTopicReplayer:
    """Relit les topics capteurs entre deux instants et repasse chaque message
    dans la chaîne d'ingestion normale.

    Sans danger pour les données déjà enregistrées : l'identifiant d'une mesure
    est dérivé de sa position Kafka (topic, partition, offset), le module
    Database ignore donc tout message déjà persisté et n'ajoute que les
    mesures manquantes (rejetées ou perdues). Les partitions sont assignées
    directement et aucun offset n'est validé : le consommateur temps réel
    n'est pas affecté.
    """

    METADATA_TIMEOUT_SECONDS = 10.0
    MAX_IDLE_POLLS = 30

    def __init__(self, consumer, handler, publisher, *, batch_size=500, on_batch=None):
        self._consumer = consumer
        self._handler = handler
        self._publisher = publisher
        self._batch_size = batch_size
        self._on_batch = on_batch or (lambda: None)

    def plan(self, topics, *, since_ms) -> dict:
        """``{(topic, partition): (premier offset, offset de fin exclu)}`` à relire."""
        requested = []
        for topic in topics:
            metadata = self._consumer.list_topics(topic, timeout=self.METADATA_TIMEOUT_SECONDS).topics.get(topic)
            if metadata is None or metadata.error is not None:
                logger.warning("Topic introuvable, ignoré : %s", topic)
                continue
            requested.extend(TopicPartition(topic, partition, since_ms) for partition in sorted(metadata.partitions))
        if not requested:
            return {}
        plan = {}
        for start in self._consumer.offsets_for_times(requested, timeout=self.METADATA_TIMEOUT_SECONDS):
            _, high = self._consumer.get_watermark_offsets(
                TopicPartition(start.topic, start.partition), timeout=self.METADATA_TIMEOUT_SECONDS, cached=False
            )
            first = start.offset if start.offset >= 0 else high
            if first < high:
                plan[(start.topic, start.partition)] = (first, high)
        return plan

    def replay(self, plan, *, until_ms=None) -> ReplayReport:
        report = ReplayReport(planned=sum(end - first for first, end in plan.values()))
        if not plan:
            return report
        remaining = {key: end for key, (_, end) in plan.items()}
        self._consumer.assign([TopicPartition(topic, partition, first) for (topic, partition), (first, _) in plan.items()])
        idle = 0
        while remaining:
            messages = self._consumer.consume(self._batch_size, timeout=1.0)
            if not messages:
                idle += 1
                if idle >= self.MAX_IDLE_POLLS:
                    logger.warning("Plus aucun message reçu : rejeu interrompu (partitions restantes : %s).", sorted(remaining))
                    break
                continue
            idle = 0
            batch = []
            for message in messages:
                if message.error():
                    logger.error("Erreur Kafka pendant le rejeu : %s", message.error())
                    continue
                key = (message.topic(), message.partition())
                end = remaining.get(key)
                if end is None or message.offset() >= end:
                    continue
                _, timestamp_ms = message.timestamp()
                if until_ms is not None and timestamp_ms is not None and timestamp_ms > until_ms:
                    self._finish(remaining, key)
                    continue
                if message.offset() >= end - 1:
                    self._finish(remaining, key)
                batch.append(self._inbound(message, timestamp_ms))
            self._process(batch, report)
        return report

    def _process(self, batch, report):
        if not batch:
            return
        self._on_batch()
        self._call(self._publisher, "begin_batch")
        try:
            for inbound in batch:
                report.read += 1
                try:
                    self._handler.handle(inbound)
                except MessageRejected as exc:
                    report.reject(exc)
                else:
                    report.accepted += 1
            # Attend les accusés du lot : lève MessagingUnavailable en cas d'échec.
            self._call(self._publisher, "end_batch")
        finally:
            self._call(self._publisher, "discard_batch")

    def _finish(self, remaining, key):
        remaining.pop(key, None)
        self._consumer.pause([TopicPartition(*key)])

    @staticmethod
    def _inbound(message, timestamp_ms):
        return InboundMessage(
            topic=message.topic(),
            value=message.value(),
            key=message.key(),
            partition=message.partition(),
            offset=message.offset(),
            timestamp_ms=timestamp_ms if timestamp_ms is not None and timestamp_ms >= 0 else None,
        )

    @staticmethod
    def _call(publisher, name):
        method = getattr(publisher, name, None)
        if method is not None:
            method()
