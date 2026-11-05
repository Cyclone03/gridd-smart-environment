import threading
import time

from django.test import SimpleTestCase

from shared.contracts.event_types import EventTypes
from shared.messaging import CommandTimeout, Event
from shared.messaging.command_gateway import CommandGateway
from shared.messaging.event_publisher import EventPublisher
from shared.messaging.kafka_reply_listener import KafkaReplyListener
from shared.messaging.reply_handler import ReplyHandler
from shared.messaging.reply_registry import ReplyRegistry


class RemoteModulePublisher(EventPublisher):
    """Publication asynchrone, comme Kafka : un « module distant » répond
    depuis un autre thread après un délai."""

    is_synchronous = False

    def __init__(self, registry, delay, answer=True):
        self._registry = registry
        self._delay = delay
        self._answer = answer

    def publish_raw(self, topic, value, key=None):
        command = Event.decode(value)

        def respond():
            time.sleep(self._delay)
            if self._answer:
                self._registry.resolve(command.reply(EventTypes.COMMAND_SUCCEEDED, {"data": {"ok": True}}, "remote"))

        threading.Thread(target=respond, daemon=True).start()


class KafkaModeCommandGatewayTests(SimpleTestCase):
    def test_waits_for_a_reply_coming_from_another_thread(self):
        registry = ReplyRegistry()
        started = []
        gateway = CommandGateway(
            RemoteModulePublisher(registry, delay=0.05),
            registry,
            reply_topic="replies",
            timeout=2,
            before_send=lambda: started.append(True),
        )
        self.assertEqual(gateway.send("commands", "x.do", {}, source="test"), {"ok": True})
        self.assertEqual(started, [True], "l'écoute des réponses démarre avant l'envoi")

    def test_times_out_when_the_module_does_not_answer(self):
        registry = ReplyRegistry()
        gateway = CommandGateway(RemoteModulePublisher(registry, 0, answer=False), registry, reply_topic="r", timeout=0.1)
        with self.assertRaises(CommandTimeout):
            gateway.send("commands", "x.do", {}, source="test")


class FakeTopicMetadata:
    error = None
    partitions = {0: object(), 1: object()}


class FakeReplyConsumer:
    """Consumer confluent-kafka simulé : deux partitions, une réponse à lire."""

    def __init__(self, reply):
        self.assigned = None
        self._messages = [reply]

    def list_topics(self, topic, timeout):
        return type("Metadata", (), {"topics": {topic: FakeTopicMetadata()}})()

    def get_watermark_offsets(self, partition, timeout):
        return (0, 40 + partition.partition)

    def assign(self, partitions):
        self.assigned = [(item.partition, item.offset) for item in partitions]

    def poll(self, timeout):
        if self._messages:
            event = self._messages.pop()
            return type(
                "Message",
                (),
                {
                    "error": lambda self: None,
                    "topic": lambda self: "replies",
                    "value": lambda self: event.encode(),
                    "key": lambda self: None,
                },
            )()
        time.sleep(0.01)
        return None


class KafkaReplyListenerTests(SimpleTestCase):
    def test_assigns_current_end_offsets_and_resolves_replies(self):
        registry = ReplyRegistry()
        future = registry.expect("c-42")
        reply = Event(type=EventTypes.COMMAND_SUCCEEDED, payload={"data": {}}, correlation_id="c-42")
        consumer = FakeReplyConsumer(reply)
        listener = KafkaReplyListener(lambda: consumer, "replies", ReplyHandler(registry))

        listener.ensure_started()
        listener.ensure_started()  # idempotent

        self.assertEqual(consumer.assigned, [(0, 40), (1, 41)])
        self.assertEqual(future.result(timeout=2).correlation_id, "c-42")
