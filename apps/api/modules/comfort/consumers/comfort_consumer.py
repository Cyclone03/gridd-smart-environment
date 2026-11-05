from modules.comfort.domain.comfort_assessor import ComfortAssessor
from modules.comfort.producers.comfort_events_producer import ComfortEventsProducer
from modules.comfort.repositories.comfort_reading_repository import ComfortReadingRepository
from modules.comfort.repositories.comfort_settings_repository import ComfortSettingsRepository
from modules.comfort.services.comfort_evaluation_service import ComfortEvaluationService
from shared.contracts.event_types import EventTypes
from shared.messaging import EventHandler, Messaging


class ComfortConsumer(EventHandler):
    """Point d'entrée Kafka du module Comfort : chaque observation persistée."""

    def __init__(self, evaluation):
        self._evaluation = evaluation

    @classmethod
    def build(cls):
        return cls(
            ComfortEvaluationService(
                settings_repository=ComfortSettingsRepository(),
                readings=ComfortReadingRepository(),
                assessor=ComfortAssessor(),
                producer=ComfortEventsProducer(Messaging.current().publisher()),
            )
        )

    def routes(self):
        return {EventTypes.OBSERVATION_PERSISTED: lambda event: self._evaluation.evaluate(event.payload)}
