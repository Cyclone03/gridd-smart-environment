from shared.contracts.event_types import EventTypes
from shared.contracts.topics import Topics
from shared.messaging import Event


class ValidatedObservationProducer:
    """Publie les observations validées dans le topic de sortie de l'ingestion.

    Clé de partition : le code de zone, pour que les mesures d'une même zone
    soient traitées dans l'ordre par les modules en aval.
    """

    SOURCE = "ingestion"

    def __init__(self, publisher):
        self._publisher = publisher

    def publish(self, payload):
        event = Event(type=EventTypes.OBSERVATION_VALIDATED, payload=payload, source=self.SOURCE)
        self._publisher.publish(Topics.ingestion_observations(), event, key=payload["zone"]["code"])
