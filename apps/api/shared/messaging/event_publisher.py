from abc import ABC, abstractmethod

from .event import Event


class EventPublisher(ABC):
    """Publication de messages sur un topic."""

    # Vrai si la publication remet le message aux abonnés avant de rendre la
    # main (bus mémoire). Faux avec Kafka.
    is_synchronous = False

    def publish(self, topic: str, event: Event, key: str | None = None) -> None:
        self.publish_raw(topic, event.encode(), key)

    @abstractmethod
    def publish_raw(self, topic: str, value: bytes, key: str | None = None) -> None:
        raise NotImplementedError
