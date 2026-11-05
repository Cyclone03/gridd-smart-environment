from .event import Event
from .message_handler import MessageHandler


class ReplyHandler(MessageHandler):
    """Remet les réponses reçues aux commandes qui les attendent."""

    def __init__(self, registry):
        self._registry = registry

    def handle(self, message):
        event = Event.decode(message.value)
        if event.correlation_id:
            self._registry.resolve(event)
