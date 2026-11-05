from shared.module_config import ModuleConfig


class RealtimeConfig(ModuleConfig):
    """Module Realtime : WebSocket des tableaux de bord (mesures, alertes,
    confort, énergie), alimenté par les faits persistés (``database.events``)."""

    name = "modules.realtime"
    label = "realtime"
    verbose_name = "GRIDD — temps réel"

    def subscriptions(self):
        from shared.contracts.topics import Topics
        from shared.messaging import Subscription

        from .consumers.realtime_consumer import RealtimeConsumer

        return [Subscription(name="realtime", topics=(Topics.database_events(),), handler_factory=RealtimeConsumer.build)]
