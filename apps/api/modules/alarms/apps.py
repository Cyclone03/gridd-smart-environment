from shared.module_config import ModuleConfig


class AlarmsConfig(ModuleConfig):
    """Module Alarms : règles d'alarme (API), évaluation des mesures et
    alertes de qualité, consultation des alertes."""

    name = "modules.alarms"
    label = "alarms"
    verbose_name = "GRIDD — alarmes"

    def subscriptions(self):
        from shared.contracts.topics import Topics
        from shared.messaging import Subscription

        from .consumers.alarms_consumer import AlarmsConsumer

        return [Subscription(name="alarms", topics=(Topics.database_events(),), handler_factory=AlarmsConsumer.build)]
