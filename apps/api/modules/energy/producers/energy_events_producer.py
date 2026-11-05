from shared.contracts.event_types import EventTypes
from shared.contracts.topics import Topics
from shared.messaging import Event


class EnergyEventsProducer:
    """Publie les estimations d'énergie dans le topic de sortie du module."""

    SOURCE = "energy"

    def __init__(self, publisher):
        self._publisher = publisher

    def estimated(self, payload):
        event = Event(type=EventTypes.ENERGY_ESTIMATED, payload=payload, source=self.SOURCE)
        self._publisher.publish(Topics.energy_events(), event, key=payload["zone_code"])
