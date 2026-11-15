from concurrent.futures import Future
from io import StringIO
from types import SimpleNamespace
from unittest import mock

from confluent_kafka import ConsumerGroupTopicPartitions, TopicPartition
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

from shared.messaging.consumer_group_inspector import ConsumerGroupInspector

TOPIC = "gridd.backend.ingestion.observations"


def done(value):
    future = Future()
    future.set_result(value)
    return future


class FakeAdmin:
    """Situation observée : une autre instance lit la partition p1 (4 zones)."""

    def describe_consumer_groups(self, groups, request_timeout=None):
        def member(client_id, host, partitions):
            return SimpleNamespace(
                client_id=client_id,
                host=host,
                assignment=SimpleNamespace(topic_partitions=[TopicPartition(TOPIC, p) for p in partitions]),
            )

        return {
            groups[0]: done(
                SimpleNamespace(
                    state=SimpleNamespace(name="STABLE"),
                    members=[
                        member("gridd-backend.database@serveur:12", "/10.0.0.2", [0, 2]),
                        member("rdkafka", "/10.0.0.9", [1]),
                    ],
                )
            )
        }

    def list_consumer_group_offsets(self, request, request_timeout=None):
        group = request[0].group_id
        offsets = [TopicPartition(TOPIC, 0, 100), TopicPartition(TOPIC, 1, 40), TopicPartition(TOPIC, 2, 90)]
        return {group: done(ConsumerGroupTopicPartitions(group, offsets))}

    def list_topics(self, timeout=None):
        return SimpleNamespace(topics={TOPIC: SimpleNamespace(partitions={0: None, 1: None, 2: None})})

    def list_offsets(self, requests, request_timeout=None):
        ends = {0: 100, 1: 500, 2: 95}
        return {tp: done(SimpleNamespace(offset=ends[tp.partition])) for tp in requests}


class ConsumerGroupInspectorTests(SimpleTestCase):
    def test_reports_members_owners_and_lag(self):
        status = ConsumerGroupInspector(FakeAdmin()).inspect("gridd-backend.database", (TOPIC,))
        self.assertEqual(status.state, "STABLE")
        self.assertEqual(len(status.members), 2)
        rows = {item.partition: item for item in status.partitions}
        self.assertEqual(rows[1].owner, "rdkafka (/10.0.0.9)")
        self.assertEqual([rows[p].lag for p in (0, 1, 2)], [0, 460, 5])

    @override_settings(EVENT_BUS="kafka", KAFKA_CONSUMER_GROUP_PREFIX="gridd-backend")
    def test_command_flags_a_shared_consumer_group(self):
        out = StringIO()
        with mock.patch("shared.messaging.kafka_client_factory.KafkaClientFactory.admin", return_value=FakeAdmin()):
            call_command("kafka_groups", "--module", "database", stdout=out)
        text = out.getvalue()
        self.assertIn("gridd-backend.database", text)
        self.assertIn("plusieurs membres", text)
        self.assertIn("lu par=rdkafka (/10.0.0.9)", text)
        self.assertIn("KAFKA_CONSUMER_GROUP_PREFIX", text)
