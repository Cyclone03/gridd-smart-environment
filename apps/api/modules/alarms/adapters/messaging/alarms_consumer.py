from shared.kernel.events import EventTypes
from shared.messaging import EventHandler


class AlarmsConsumer(EventHandler):
    """Point d'entrée Kafka du moteur d'alarmes.

    - ``observation.persisted`` : alertes de qualité, puis règles d'alarme ;
    - ``alarm_rule.changed`` : effets d'une modification de règle.

    Assemblé par ``modules.alarms.composition.alarms_consumer``.
    """

    def __init__(self, *, quality_alerts, rule_evaluation, rule_changes):
        self._quality_alerts = quality_alerts
        self._rule_evaluation = rule_evaluation
        self._rule_changes = rule_changes

    def routes(self):
        return {
            EventTypes.OBSERVATION_PERSISTED: self._on_observation,
            EventTypes.ALARM_RULE_CHANGED: lambda event: self._rule_changes.apply(event.payload),
        }

    def _on_observation(self, event):
        self._quality_alerts.process(event.payload)
        self._rule_evaluation.evaluate(event.payload)
