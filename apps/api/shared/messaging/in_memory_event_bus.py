import logging

from .event_publisher import EventPublisher
from .inbound_message import InboundMessage
from .message_rejected import MessageRejected

logger = logging.getLogger(__name__)


class InMemoryEventBus(EventPublisher):
    """Bus synchrone dans le processus courant (tests, développement sans Kafka).

    Chaque publication est remise immédiatement aux abonnés du topic, dans
    l'ordre d'abonnement. Comme avec Kafka, l'échec d'un abonné n'interrompt
    ni l'émetteur ni les autres abonnés : il est journalisé.
    """

    is_synchronous = True

    def __init__(self):
        self._subscriptions = []
        self._handlers = {}

    def subscribe(self, subscription):
        self._subscriptions.append(subscription)

    def publish_raw(self, topic, value, key=None):
        message = InboundMessage(
            topic=topic,
            value=value,
            key=key.encode("utf-8") if isinstance(key, str) else key,
        )
        for subscription in list(self._subscriptions):
            if topic in subscription.topics:
                self._deliver(subscription, message)

    def _deliver(self, subscription, message):
        try:
            self._handler_for(subscription).handle(message)
        except MessageRejected as exc:
            logger.warning("[%s] message rejeté sur %s : %s", subscription.name, message.topic, exc)
        except Exception:
            logger.exception("[%s] échec du traitement d'un message de %s.", subscription.name, message.topic)

    def _handler_for(self, subscription):
        handler = self._handlers.get(subscription.name)
        if handler is None:
            handler = subscription.handler_factory()
            self._handlers[subscription.name] = handler
        return handler
