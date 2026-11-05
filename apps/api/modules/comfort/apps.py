from shared.module_config import ModuleConfig


class ComfortConfig(ModuleConfig):
    """Module Comfort : confort thermique des zones d'après température et humidité."""

    name = "modules.comfort"
    label = "comfort"
    verbose_name = "GRIDD — confort thermique"

    def subscriptions(self):
        from shared.contracts.topics import Topics
        from shared.messaging import Subscription

        from .consumers.comfort_consumer import ComfortConsumer

        return [Subscription(name="comfort", topics=(Topics.database_events(),), handler_factory=ComfortConsumer.build)]
