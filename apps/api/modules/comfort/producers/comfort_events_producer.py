from shared.contracts.event_types import EventTypes
from shared.contracts.topics import Topics
from shared.messaging import Event


class ComfortEventsProducer:
    """Publie les évaluations de confort dans le topic de sortie du module."""

    SOURCE = "comfort"

    def __init__(self, publisher):
        self._publisher = publisher

    def assessed(self, payload):
        event = Event(type=EventTypes.COMFORT_ASSESSED, payload=payload, source=self.SOURCE)
        self._publisher.publish(Topics.comfort_events(), event, key=payload["zone_code"])
