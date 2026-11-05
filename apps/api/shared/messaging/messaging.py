import threading

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from shared.contracts.topics import Topics

from .command_gateway import CommandGateway
from .in_memory_event_bus import InMemoryEventBus
from .kafka_client_factory import KafkaClientFactory
from .kafka_connection_config import KafkaConnectionConfig
from .kafka_consumer_runner import KafkaConsumerRunner
from .kafka_event_publisher import KafkaEventPublisher
from .kafka_reply_listener import KafkaReplyListener
from .reply_handler import ReplyHandler
from .reply_registry import ReplyRegistry
from .subscription import Subscription
from .subscription_registry import SubscriptionRegistry
from .topic_provisioner import TopicProvisioner


class Messaging:
    """Assemble l'infrastructure de messagerie du processus (racine de composition).

    ``EVENT_BUS=kafka`` (production) : publication sur Kafka ; la consommation
    est assurée par ``manage.py run_consumers``, la réception des réponses aux
    commandes par un thread d'écoute démarré à la première commande.

    ``EVENT_BUS=memory`` (tests, développement sans Kafka) : bus synchrone en
    mémoire sur lequel tous les abonnements des modules sont branchés ; un
    processus exécute alors toute la chaîne de traitement.
    """

    MODES = ("memory", "kafka")
    CONNECTIONS = ("main", "sensors")

    _current = None
    _lock = threading.Lock()

    @classmethod
    def current(cls) -> "Messaging":
        with cls._lock:
            if cls._current is None:
                cls._current = cls(settings.EVENT_BUS)
            return cls._current

    @classmethod
    def reset(cls):
        """Oublie l'instance courante (tests, changement de configuration)."""
        with cls._lock:
            cls._current = None

    def __init__(self, mode):
        if mode not in self.MODES:
            raise ImproperlyConfigured(f"EVENT_BUS doit valoir {' ou '.join(self.MODES)} (reçu : {mode!r}).")
        self.mode = mode
        self._registry = ReplyRegistry()
        self._publishers = {}
        self._reply_listener = None
        self._factories = {}
        if mode == "memory":
            self._build_memory_bus()
        else:
            self._factories = {name: KafkaClientFactory(KafkaConnectionConfig.from_settings(name)) for name in self.CONNECTIONS}

    @property
    def is_kafka(self) -> bool:
        return self.mode == "kafka"

    def publisher(self, connection="main"):
        if connection not in self._publishers:
            factory = self._factories[connection]
            same_cluster = next(
                (name for name, other in self._factories.items() if name in self._publishers and other.config == factory.config),
                None,
            )
            self._publishers[connection] = (
                self._publishers[same_cluster]
                if same_cluster
                else KafkaEventPublisher(factory.producer(), settings.KAFKA_PUBLISH_TIMEOUT_SECONDS)
            )
        return self._publishers[connection]

    def gateway(self) -> CommandGateway:
        return CommandGateway(
            self.publisher(),
            self._registry,
            reply_topic=Topics.database_replies(),
            timeout=settings.KAFKA_COMMAND_TIMEOUT_SECONDS,
            before_send=self._start_reply_listener if self.is_kafka else None,
        )

    def consumer_runner(self) -> KafkaConsumerRunner:
        self._require_kafka()
        return KafkaConsumerRunner(
            self._factories,
            group_prefix=settings.KAFKA_CONSUMER_GROUP_PREFIX,
            max_attempts=settings.KAFKA_MAX_ATTEMPTS,
            retry_delay=settings.KAFKA_RETRY_DELAY_SECONDS,
        )

    def topic_provisioner(self) -> TopicProvisioner:
        self._require_kafka()
        return TopicProvisioner(
            self._factories["main"].admin(),
            partitions=settings.KAFKA_TOPIC_PARTITIONS,
            replication_factor=settings.KAFKA_TOPIC_REPLICATION_FACTOR,
        )

    def _build_memory_bus(self):
        bus = InMemoryEventBus()
        for subscription in SubscriptionRegistry().all():
            bus.subscribe(subscription)
        bus.subscribe(
            Subscription(
                name="replies",
                topics=(Topics.database_replies(),),
                handler_factory=lambda: ReplyHandler(self._registry),
            )
        )
        self._publishers = {name: bus for name in self.CONNECTIONS}

    def _start_reply_listener(self):
        if self._reply_listener is None:
            factory = self._factories["main"]
            self._reply_listener = KafkaReplyListener(
                consumer_factory=lambda: factory.consumer(f"{settings.KAFKA_CONSUMER_GROUP_PREFIX}.replies"),
                topic=Topics.database_replies(),
                handler=ReplyHandler(self._registry),
            )
        self._reply_listener.ensure_started()

    def _require_kafka(self):
        if not self.is_kafka:
            raise ImproperlyConfigured("Opération réservée à EVENT_BUS=kafka.")
