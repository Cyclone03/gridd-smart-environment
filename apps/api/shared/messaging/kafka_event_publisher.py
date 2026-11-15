import threading

from .delivery_tracker import DeliveryTracker
from .event_publisher import EventPublisher
from .messaging_unavailable import MessagingUnavailable


class KafkaEventPublisher(EventPublisher):
    """Publication sur Kafka.

    Deux modes :

    - **hors lot** (API, commandes) : chaque publication attend l'accusé de
      réception du broker avant de rendre la main ;
    - **en lot** (consommateurs, entre ``begin_batch()`` et ``end_batch()``
      dans un même thread) : les messages partent sans attente et
      ``end_batch()`` attend en une fois tous les accusés du lot. Le
      consommateur ne valide ses offsets qu'après ``end_batch()`` : aucune
      perte entre deux modules, mais un seul aller-retour réseau par lot au
      lieu d'un par message (c'était le goulot d'étranglement : quelques
      messages par seconde avec un broker distant).

    Le producteur n'est créé qu'à la première publication : un processus qui
    ne fait que lire (requête GET de l'API) n'a pas besoin de joindre Kafka.
    """

    BUFFER_FULL_WAIT_SECONDS = 1.0

    def __init__(self, producer_factory, flush_timeout=10.0):
        self._producer_factory = producer_factory
        self._producer_instance = None
        self._lock = threading.Lock()
        self._flush_timeout = flush_timeout
        self._local = threading.local()

    @property
    def _producer(self):
        with self._lock:
            if self._producer_instance is None:
                self._producer_instance = self._producer_factory()
        return self._producer_instance

    def begin_batch(self):
        self._local.batch = DeliveryTracker()

    def end_batch(self):
        """Attend les accusés du lot du thread courant ; lève ``MessagingUnavailable`` en cas d'échec."""
        tracker = getattr(self._local, "batch", None)
        self._local.batch = None
        if tracker is not None:
            self._confirm(tracker, "lot")

    def discard_batch(self):
        self._local.batch = None

    def publish_raw(self, topic, value, key=None):
        batch = getattr(self._local, "batch", None)
        tracker = batch or DeliveryTracker()
        self._produce(topic, value, key, tracker)
        if batch is None:
            self._confirm(tracker, topic)
        else:
            # Sert les accusés déjà arrivés, sans attendre.
            self._producer.poll(0)

    def _produce(self, topic, value, key, tracker):
        try:
            self._producer.produce(topic, value=value, key=key, on_delivery=tracker.on_delivery)
        except BufferError:
            # File locale pleine : laisser partir des messages puis réessayer une fois.
            self._producer.poll(self.BUFFER_FULL_WAIT_SECONDS)
            try:
                self._producer.produce(topic, value=value, key=key, on_delivery=tracker.on_delivery)
            except BufferError as exc:
                raise MessagingUnavailable(f"File d'envoi Kafka pleine pour {topic}.") from exc
        tracker.sent()

    def _confirm(self, tracker, label):
        if tracker.outstanding:
            self._producer.flush(self._flush_timeout)
        error = tracker.first_error
        if error is not None or tracker.outstanding:
            raise MessagingUnavailable(f"Publication impossible ({label}) : {error or 'délai dépassé'}")
