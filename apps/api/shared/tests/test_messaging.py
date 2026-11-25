import threading

from confluent_kafka import OFFSET_END
from django.test import SimpleTestCase

from shared.kernel.events.event_types import EventTypes
from shared.messaging import (
    CommandFailed,
    CommandTimeout,
    Event,
    MessageHandler,
    MessageRejected,
    MessagingUnavailable,
    Subscription,
)
from shared.messaging.command_gateway import CommandGateway
from shared.messaging.in_memory_event_bus import InMemoryEventBus
from shared.messaging.kafka_consumer_runner import KafkaConsumerRunner
from shared.messaging.kafka_event_publisher import KafkaEventPublisher
from shared.messaging.kafka_subscription_worker import KafkaSubscriptionWorker
from shared.messaging.partition_assignment_monitor import PartitionAssignmentMonitor
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
    def __init__(self, offset, partition=0):
        self._offset = offset
        self._partition = partition

    def error(self):
        return None

    def topic(self):
        return "t1"

    def value(self):
        return b"{}"

    def key(self):
        return None

    def partition(self):
        return self._partition

    def offset(self):
        return self._offset

    def timestamp(self):
        return (1, 1_700_000_000_000)


class FakeConsumer:
    """Enregistre le dernier offset traité de chaque validation (offset validé - 1)."""

    def __init__(self):
        self.commits = []
        self.commit_calls = 0
        self.seeks = []

    def commit(self, offsets, asynchronous):
        self.commit_calls += 1
        self.commits.extend(tp.offset - 1 for tp in offsets)

    def seek(self, partition):
        self.seeks.append((partition.partition, partition.offset))


class FakePublisher:
    """Publisher en lot dont la confirmation peut échouer."""

    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def begin_batch(self):
        self.calls.append("begin")

    def end_batch(self):
        self.calls.append("end")
        if self.fail:
            raise MessagingUnavailable("broker indisponible")

    def discard_batch(self):
        self.calls.append("discard")


class KafkaSubscriptionWorkerTests(SimpleTestCase):
    def worker(self, handler, max_attempts=3, publishers=(), factory=None):
        consumer = FakeConsumer()
        worker = KafkaSubscriptionWorker(
            Subscription("test", ("t1",), factory or (lambda: handler)),
            consumer,
            stop_event=threading.Event(),
            live_edge=False,
            max_attempts=max_attempts,
            retry_delay=0,
            publishers=publishers,
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


    def test_batch_is_confirmed_then_committed_once(self):
        handler = RecordingHandler()
        publisher = FakePublisher()
        worker, consumer = self.worker(handler, publishers=[publisher])
        worker.process_batch([FakeKafkaMessage(3, 0), FakeKafkaMessage(4, 0), FakeKafkaMessage(9, 1)])
        self.assertEqual(len(handler.messages), 3)
        self.assertEqual(publisher.calls, ["begin", "end", "discard"])
        self.assertEqual(consumer.commit_calls, 1)  # un seul aller-retour pour tout le lot
        self.assertEqual(sorted(consumer.commits), [4, 9])  # dernier offset de chaque partition

    def test_unconfirmed_publications_rewind_the_batch_without_commit(self):
        built = []

        def factory():
            built.append(RecordingHandler())
            return built[-1]

        worker, consumer = self.worker(None, publishers=[FakePublisher(fail=True)], factory=factory)
        worker._handler = factory()
        with self.assertLogs("shared.messaging.kafka_subscription_worker", level="ERROR"):
            worker.process_batch([FakeKafkaMessage(10, 0), FakeKafkaMessage(11, 0), FakeKafkaMessage(5, 2)])
        self.assertEqual(consumer.commits, [])
        self.assertEqual(sorted(consumer.seeks), [(0, 10), (2, 5)])
        self.assertEqual(len(built), 2)  # caches locaux reconstruits depuis la base

    def test_handler_batch_hooks_wrap_the_batch(self):
        class BatchingHandler(RecordingHandler):
            def __init__(self):
                super().__init__()
                self.calls = []

            def begin_batch(self):
                self.calls.append("begin")

            def end_batch(self):
                self.calls.append(f"end:{len(self.messages)}")

        handler = BatchingHandler()
        worker, _ = self.worker(handler)
        worker.process_batch([FakeKafkaMessage(1), FakeKafkaMessage(2)])
        self.assertEqual(handler.calls, ["begin", "end:2"])


class KafkaEventPublisherTests(SimpleTestCase):
    class Producer:
        """Accusés de réception rendus uniquement par flush (aller-retour réseau)."""

        def __init__(self, fail=False):
            self.fail = fail
            self.pending = []
            self.flushes = 0

        def produce(self, topic, value=None, key=None, on_delivery=None):
            self.pending.append(on_delivery)

        def poll(self, timeout=0):
            return 0

        def flush(self, timeout=None):
            self.flushes += 1
            pending, self.pending = self.pending, []
            for callback in pending:
                callback("échec" if self.fail else None, None)
            return 0

    def test_outside_a_batch_each_publication_is_confirmed(self):
        producer = self.Producer()
        publisher = KafkaEventPublisher(lambda: producer)
        publisher.publish_raw("t", b"1")
        publisher.publish_raw("t", b"2")
        self.assertEqual(producer.flushes, 2)

    def test_a_batch_is_confirmed_in_a_single_round_trip(self):
        producer = self.Producer()
        publisher = KafkaEventPublisher(lambda: producer)
        publisher.begin_batch()
        for value in range(50):
            publisher.publish_raw("t", str(value).encode())
        self.assertEqual(producer.flushes, 0)
        publisher.end_batch()
        self.assertEqual(producer.flushes, 1)

    def test_delivery_failure_is_reported_at_the_end_of_the_batch(self):
        publisher = KafkaEventPublisher(lambda: self.Producer(fail=True))
        publisher.begin_batch()
        publisher.publish_raw("t", b"1")
        with self.assertRaises(MessagingUnavailable):
            publisher.end_batch()


class PartitionAssignmentMonitorTests(SimpleTestCase):
    class Partition:
        def __init__(self, topic, partition, offset=123):
            self.topic, self.partition, self.offset = topic, partition, offset

    class Consumer:
        """Consumer minimal : métadonnées d'un topic à 3 partitions."""

        def __init__(self):
            self.assigned = None

        def assign(self, partitions):
            self.assigned = partitions

        def list_topics(self, topic, timeout=None):
            metadata = type("TopicMetadata", (), {"partitions": {0: None, 1: None, 2: None}, "error": None})()
            return type("ClusterMetadata", (), {"topics": {topic: metadata}})()

    def test_live_assignment_ignores_committed_backlog(self):
        consumer = self.Consumer()
        partitions = [self.Partition("capteurs", 0), self.Partition("capteurs", 1)]
        PartitionAssignmentMonitor("ingestion", ("capteurs",), live_edge=True).on_assign(consumer, partitions)
        self.assertIs(consumer.assigned, partitions)
        self.assertTrue(all(partition.offset == OFFSET_END for partition in partitions))

    def test_regular_assignment_keeps_committed_offsets(self):
        consumer = self.Consumer()
        partitions = [self.Partition("obs", 0)]
        PartitionAssignmentMonitor("database", ("obs",)).on_assign(consumer, partitions)
        self.assertEqual(partitions[0].offset, 123)

    def test_warns_when_another_member_reads_some_partitions(self):
        consumer = self.Consumer()
        monitor = PartitionAssignmentMonitor("database", ("obs",))
        with self.assertLogs("shared.messaging.partition_assignment_monitor", level="INFO") as logs:
            monitor.on_assign(consumer, [self.Partition("obs", 0), self.Partition("obs", 2)])
            monitor.check(consumer)
            monitor.check(consumer)  # une seule vérification par rééquilibrage
        warnings = [line for line in logs.output if line.startswith("WARNING")]
        self.assertEqual(len(warnings), 1)
        self.assertIn("obs [p1]", warnings[0])
        self.assertIn("partitions attribuées : obs [p0, p2]", logs.output[0])

    def test_no_warning_when_all_partitions_are_assigned(self):
        consumer = self.Consumer()
        monitor = PartitionAssignmentMonitor("database", ("obs",))
        with self.assertLogs("shared.messaging.partition_assignment_monitor", level="INFO") as logs:
            monitor.on_assign(consumer, [self.Partition("obs", n) for n in range(3)])
            monitor.check(consumer)
        self.assertFalse([line for line in logs.output if line.startswith("WARNING")])


class KafkaConsumerRunnerWatchTests(SimpleTestCase):
    class Worker:
        def __init__(self, last_progress):
            self.last_progress = last_progress

    def runner(self, now, heartbeat_file=None):
        exits = []
        runner = KafkaConsumerRunner(
            {},
            group_prefix="g",
            max_attempts=1,
            retry_delay=0,
            stall_seconds=300,
            heartbeat_file=heartbeat_file,
            clock=lambda: now,
            exit=exits.append,
        )
        return runner, exits

    def test_heartbeat_while_every_module_progresses(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as folder:
            beat = Path(folder) / "beat"
            runner, exits = self.runner(1000, heartbeat_file=beat)
            runner.watch([("database", self.Worker(990)), ("alarms", self.Worker(999))])
            self.assertTrue(beat.exists())
            self.assertEqual(exits, [])

    def test_a_stalled_module_stops_the_process(self):
        runner, exits = self.runner(1000)
        with self.assertLogs("shared.messaging.kafka_consumer_runner", level="CRITICAL") as logs:
            runner.watch([("database", self.Worker(600)), ("alarms", self.Worker(999))])
        self.assertEqual(exits, [KafkaConsumerRunner.STALL_EXIT_CODE])
        self.assertIn("database", logs.output[0])


class PoisonBatchTests(SimpleTestCase):
    """Un lot qui échoue toujours ne doit jamais bloquer une partition."""

    def test_failing_batches_shrink_then_the_lone_message_is_abandoned(self):
        consumer = FakeConsumer()
        worker = KafkaSubscriptionWorker(
            Subscription("test", ("t1",), RecordingHandler),
            consumer,
            stop_event=threading.Event(),
            live_edge=False,
            max_attempts=3,
            retry_delay=0,
            publishers=[FakePublisher(fail=True)],
            batch_size=500,
            sleep=lambda _: None,
        )
        worker._handler = RecordingHandler()
        with self.assertLogs("shared.messaging.kafka_subscription_worker", level="ERROR") as logs:
            worker.process_batch([FakeKafkaMessage(offset) for offset in range(100, 400)])
            self.assertEqual(worker._current_batch_size, 30)
            worker.process_batch([FakeKafkaMessage(offset) for offset in range(100, 130)])
            self.assertEqual(worker._current_batch_size, 3)
            worker.process_batch([FakeKafkaMessage(100)])
        self.assertEqual(consumer.commits, [100])  # abandonné puis validé : la partition avance
        self.assertTrue(any("message abandonné" in line for line in logs.output))


class BatchHookFailureTests(SimpleTestCase):
    def test_a_failing_end_of_batch_rewinds_instead_of_crashing(self):
        class FailingHandler(RecordingHandler):
            def end_batch(self):
                raise RuntimeError("base indisponible")

        consumer = FakeConsumer()
        worker = KafkaSubscriptionWorker(
            Subscription("test", ("t1",), FailingHandler),
            consumer,
            stop_event=threading.Event(),
            live_edge=False,
            max_attempts=3,
            retry_delay=0,
            sleep=lambda _: None,
        )
        worker._handler = FailingHandler()
        with self.assertLogs("shared.messaging.kafka_subscription_worker", level="ERROR"):
            worker.process_batch([FakeKafkaMessage(1), FakeKafkaMessage(2)])
        self.assertEqual(consumer.commits, [])
        self.assertEqual(consumer.seeks, [(0, 1)])
