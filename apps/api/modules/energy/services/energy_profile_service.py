from modules.energy.repositories.energy_settings_repository import EnergySettingsRepository
from shared.contracts.event_types import EventTypes
from shared.contracts.topics import Topics
from shared.messaging import Messaging


class EnergyProfileService:
    """Paramètres énergétiques par zone : consultation, personnalisation, retour
    aux valeurs par défaut. Les modifications s'appliquent aux estimations
    suivantes ; les modifications sont des commandes Kafka traitées par Database."""

    SOURCE = "energy"

    def __init__(self, repository, gateway):
        self._repository = repository
        self._gateway = gateway

    @classmethod
    def build(cls):
        return cls(EnergySettingsRepository(), Messaging.current().gateway())

    def list(self):
        return self._repository.all()

    def get(self, zone_code):
        return self._repository.get(zone_code)

    def customize(self, zone_code, profile):
        self._send(EventTypes.ENERGY_PROFILE_SAVE, {"zone_code": zone_code, "profile": profile.to_dict()})
        return self._repository.get(zone_code)

    def reset(self, zone_code):
        self._send(EventTypes.ENERGY_PROFILE_RESET, {"zone_code": zone_code})
        return self._repository.get(zone_code)

    def _send(self, command_type, payload):
        self._gateway.send(Topics.energy_commands(), command_type, payload, source=self.SOURCE, key=payload["zone_code"])
