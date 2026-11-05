from shared.module_config import ModuleConfig


class EnergyConfig(ModuleConfig):
    """Module Energy : estimation de la consommation électrique des zones
    par un modèle paramétrable alimenté par les mesures."""

    name = "modules.energy"
    label = "energy"
    verbose_name = "GRIDD — énergie"

    def subscriptions(self):
        from shared.contracts.topics import Topics
        from shared.messaging import Subscription

        from .consumers.energy_consumer import EnergyConsumer

        return [Subscription(name="energy", topics=(Topics.database_events(),), handler_factory=EnergyConsumer.build)]
