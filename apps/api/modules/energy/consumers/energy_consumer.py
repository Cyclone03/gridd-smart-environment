from modules.energy.domain.energy_model import EnergyModel
from modules.energy.producers.energy_events_producer import EnergyEventsProducer
from modules.energy.repositories.energy_input_repository import EnergyInputRepository
from modules.energy.repositories.energy_settings_repository import EnergySettingsRepository
from modules.energy.services.energy_estimation_service import EnergyEstimationService
from shared.contracts.event_types import EventTypes
from shared.messaging import EventHandler, Messaging


class EnergyConsumer(EventHandler):
    """Point d'entrée Kafka du module Energy : chaque observation persistée."""

    def __init__(self, estimation):
        self._estimation = estimation

    @classmethod
    def build(cls):
        return cls(
            EnergyEstimationService(
                settings_repository=EnergySettingsRepository(),
                inputs=EnergyInputRepository(),
                model=EnergyModel(),
                producer=EnergyEventsProducer(Messaging.current().publisher()),
            )
        )

    def routes(self):
        return {EventTypes.OBSERVATION_PERSISTED: lambda event: self._estimation.estimate(event.payload)}
