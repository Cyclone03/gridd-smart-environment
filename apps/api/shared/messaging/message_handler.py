from abc import ABC, abstractmethod

from .inbound_message import InboundMessage


class MessageHandler(ABC):
    """Traitement d'un message reçu d'un topic.

    Lever ``MessageRejected`` pour un message définitivement invalide ; toute
    autre exception est considérée transitoire (nouvelle tentative).
    """

    @abstractmethod
    def handle(self, message: InboundMessage) -> None:
        raise NotImplementedError
