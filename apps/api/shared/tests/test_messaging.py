import threading

from confluent_kafka import OFFSET_END
from django.test import SimpleTestCase

from shared.contracts.event_types import EventTypes
from shared.messaging import CommandFailed, CommandTimeout, Event, MessageHandler, MessageRejected, Subscription
from shared.messaging.command_gateway import CommandGateway
from shared.messaging.in_memory_event_bus import InMemoryEventBus
from shared.messaging.kafka_subscription_worker import KafkaSubscriptionWorker
from shared.messaging.live_edge_assigner import LiveEdgeAssigner
from shared.messaging.reply_handler import ReplyHandler
from shared.messaging.reply_registry import ReplyRegistry


class RecordingHandler(MessageHandler):
    def __init__(self, failures=0, error=RuntimeError):
        self.messages = []
        self.failures = failures
        self.error = error

    def handle(self, message):
        if self.failures:
            self.failures -= 1
            raise self.error("échec")
        self.messages.append(message)


class EventTests(SimpleTestCase):
    def test_round_trip_and_invalid_envelope(self):
        event = Event(type="x.happened", payload={"value": 1.5, "nom": "é"}, source="test")
        self.assertEqual(Event.decode(event.encode()), event)
        for raw in (b"pas du json", b"[]", b'{"type": "x"}'):
            with self.subTest(raw=raw), self.assertRaises(MessageRejected):
                Event.decode(raw)


class InMemoryEventBusTests(SimpleTestCase):
    def test_delivers_to_topic_subscribers_and_isolates_failures(self):
        bus = InMemoryEventBus()
        failing, ok, other = RecordingHandler(failures=1), RecordingHandler(), RecordingHandler()
        bus.subscribe(Subscription("failing", ("t1",), lambda: failing))
        bus.subscribe(Subscription("ok", ("t1",), lambda: ok))
        bus.subscribe(Subscription("other", ("t2",), lambda: other))

        with self.assertLogs("shared.messaging.in_memory_event_bus", level="ERROR"):
            bus.publish("t1", Event(type="e", payload={}))

        self.assertEqual(len(ok.messages), 1)
        self.assertEqual(other.messages, [])


class CommandGatewayTests(SimpleTestCase):
    def setUp(self):
        self.registry = ReplyRegistry()
        self.bus = InMemoryEventBus()
        self.bus.subscribe(Subscription("replies", ("replies",), lambda: ReplyHandler(self.registry)))
        self.gateway = CommandGateway(self.bus, self.registry, reply_topic="replies", timeout=1)

    def responder(self, reply_type, payload):
        bus = self.bus

        class Responder(MessageHandler):
            def handle(self, message):
                command = Event.decode(message.value)
                bus.publish(command.reply_to, command.reply(reply_type, payload, "test"))

        self.bus.subscribe(Subscription("responder", ("commands",), Responder))

    def test_success(self):
        self.responder(EventTypes.COMMAND_SUCCEEDED, {"data": {"rule_id": 3}})
        self.assertEqual(self.gateway.send("commands", "rule.create", {}, source="test"), {"rule_id": 3})

    def test_failure_is_raised(self):
        self.responder(EventTypes.COMMAND_FAILED, {"error": {"code": "not_found", "message": "absent"}})
        with self.assertRaises(CommandFailed) as context:
            self.gateway.send("commands", "rule.delete", {}, source="test")
        self.assertEqual(context.exception.code, CommandFailed.NOT_FOUND)

    def test_missing_reply_times_out(self):
        with self.assertRaises(CommandTimeout):
            self.gateway.send("commands", "rule.create", {}, source="test")


class FakeKafkaMessage:
    def __init__(self, offset):
        self._offset = offset

    def error(self):
        return None

    def topic(self):
        return "t1"

    def value(self):
        return b"{}"

    def key(self):
        return None

    def partition(self):
        return 0

    def offset(self):
        return self._offset

    def timestamp(self):
        return (1, 1_700_000_000_000)


class FakeConsumer:
    def __init__(self):
        self.commits = []

    def commit(self, message, asynchronous):
        self.commits.append(message.offset())


class KafkaSubscriptionWorkerTests(SimpleTestCase):
    def worker(self, handler, max_attempts=3):
        consumer = FakeConsumer()
        worker = KafkaSubscriptionWorker(
            Subscription("test", ("t1",), lambda: handler),
            consumer,
            stop_event=threading.Event(),
            live_edge=False,
            max_attempts=max_attempts,
            retry_delay=0,
            sleep=lambda _: None,
        )
        worker._handler = handler
        return worker, consumer

    def test_commits_after_processing(self):
        handler = RecordingHandler()
        worker, consumer = self.worker(handler)
        worker.process(FakeKafkaMessage(5))
        self.assertEqual(consumer.commits, [5])
        self.assertEqual(handler.messages[0].timestamp_ms, 1_700_000_000_000)

    def test_transient_error_is_retried(self):
        handler = RecordingHandler(failures=2)
        worker, consumer = self.worker(handler)
        with self.assertLogs("shared.messaging.kafka_subscription_worker", level="ERROR"):
            worker.process(FakeKafkaMessage(6))
        self.assertEqual(len(handler.messages), 1)
        self.assertEqual(consumer.commits, [6])

    def test_rejected_message_is_committed_without_retry(self):
        handler = RecordingHandler(failures=5, error=MessageRejected)
        worker, consumer = self.worker(handler)
        with self.assertLogs("shared.messaging.kafka_subscription_worker", level="WARNING"):
            worker.process(FakeKafkaMessage(7))
        self.assertEqual(handler.failures, 4)
        self.assertEqual(consumer.commits, [7])

    def test_gives_up_after_max_attempts(self):
        handler = RecordingHandler(failures=10)
        worker, consumer = self.worker(handler, max_attempts=3)
        with self.assertLogs("shared.messaging.kafka_subscription_worker", level="ERROR"):
            worker.process(FakeKafkaMessage(8))
        self.assertEqual(handler.failures, 7)
        self.assertEqual(consumer.commits, [8])


class LiveEdgeAssignerTests(SimpleTestCase):
    def test_live_assignment_ignores_committed_backlog(self):
        class Partition:
            offset = 123

        class Consumer:
            assigned = None

            def assign(self, partitions):
                self.assigned = partitions

        consumer = Consumer()
        partitions = [Partition(), Partition()]
        LiveEdgeAssigner()(consumer, partitions)
        self.assertIs(consumer.assigned, partitions)
        self.assertTrue(all(partition.offset == OFFSET_END for partition in partitions))
