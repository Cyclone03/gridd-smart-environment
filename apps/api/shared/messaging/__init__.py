"""Messagerie inter-modules : enveloppe d'événement, bus Kafka ou mémoire,
consommation par module et requête-réponse corrélée.

Les modules n'importent que les éléments publics listés ici.
"""

from .command_failed import CommandFailed
from .command_timeout import CommandTimeout
from .event import Event
from .event_handler import EventHandler
from .inbound_message import InboundMessage
from .message_handler import MessageHandler
from .message_rejected import MessageRejected
from .messaging import Messaging
from .messaging_unavailable import MessagingUnavailable
from .subscription import Subscription

__all__ = [
    "CommandFailed",
    "CommandTimeout",
    "Event",
    "EventHandler",
    "InboundMessage",
    "MessageHandler",
    "MessageRejected",
    "Messaging",
    "MessagingUnavailable",
    "Subscription",
]
