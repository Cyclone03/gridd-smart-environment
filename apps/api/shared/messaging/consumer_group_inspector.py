from confluent_kafka import ConsumerGroupTopicPartitions, TopicPartition
from confluent_kafka.admin import OffsetSpec

from .group_status import GroupStatus
from .partition_status import PartitionStatus


class ConsumerGroupInspector:
    """Lecture (seule) de l'état d'un consumer group : membres, partitions
    attribuées à chacun, position validée et retard (lag) par partition.

    Sert à vérifier qu'aucune autre instance du backend ne partage le groupe :
    une partition lue par un autre membre est perdue pour cette base.
    """

    TIMEOUT_SECONDS = 10

    def __init__(self, admin):
        self._admin = admin

    def inspect(self, group, topics) -> GroupStatus:
        futures = self._admin.describe_consumer_groups([group], request_timeout=self.TIMEOUT_SECONDS)
        description = futures[group].result()
        members = []
        owners = {}
        for member in description.members:
            label = f"{member.client_id} ({member.host})"
            assigned = sorted(
                (tp.topic, tp.partition) for tp in (member.assignment.topic_partitions if member.assignment else [])
            )
            members.append((label, assigned))
            owners.update({key: label for key in assigned})

        committed = {}
        request = [ConsumerGroupTopicPartitions(group)]
        result = self._admin.list_consumer_group_offsets(request, request_timeout=self.TIMEOUT_SECONDS)[group].result()
        for tp in result.topic_partitions or []:
            committed[(tp.topic, tp.partition)] = tp.offset if tp.offset >= 0 else None

        metadata = self._admin.list_topics(timeout=self.TIMEOUT_SECONDS)
        keys = [
            (topic, partition)
            for topic in topics
            if topic in metadata.topics
            for partition in sorted(metadata.topics[topic].partitions)
        ]
        ends = {}
        if keys:
            futures = self._admin.list_offsets(
                {TopicPartition(topic, partition): OffsetSpec.latest() for topic, partition in keys},
                request_timeout=self.TIMEOUT_SECONDS,
            )
            for tp, future in futures.items():
                ends[(tp.topic, tp.partition)] = future.result().offset

        return GroupStatus(
            group=group,
            state=str(getattr(description.state, "name", description.state)),
            members=members,
            partitions=[
                PartitionStatus(*key, owner=owners.get(key), committed=committed.get(key), end=ends.get(key))
                for key in keys
            ],
        )
