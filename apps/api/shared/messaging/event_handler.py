from abc import abstractmethod
from collections.abc import Callable

from .event import Event
from .inbound_message import InboundMessage
from .message_handler import MessageHandler


class EventHandler(MessageHandler):
    """Consommateur d'événements internes.

    Décode l'enveloppe et la transmet à la méthode associée à son type. Les
    types non déclarés sont ignorés : un même topic transporte des événements
    destinés à plusieurs modules.
    """

    @abstractmethod
    def routes(self) -> dict[str, Callable[[Event], None]]:
        raise NotImplementedError

    def handle(self, message: InboundMessage) -> None:
        event = Event.decode(message.value)
        route = self.routes().get(event.type)
        if route is not None:
            route(event)
