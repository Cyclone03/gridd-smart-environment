from shared.contracts.event_types import EventTypes
from shared.contracts.topics import Topics
from shared.messaging import Event


class DatabaseEventsProducer:
    """Publie les faits persistés dans le topic de sortie du module Database."""

    SOURCE = "database"

    def __init__(self, publisher):
        self._publisher = publisher

    def observation_persisted(self, payload):
        self._publish(EventTypes.OBSERVATION_PERSISTED, payload, key=payload["zone_code"])

    def alerts_changed(self, zone_code=None):
        self._publish(EventTypes.ALERTS_CHANGED, {"zone_code": zone_code}, key=zone_code)

    def comfort_persisted(self, payload):
        self._publish(EventTypes.COMFORT_PERSISTED, payload, key=payload["zone_code"])

    def energy_persisted(self, payload):
        self._publish(EventTypes.ENERGY_PERSISTED, payload, key=payload["zone_code"])

    def alarm_rule_changed(self, *, rule, action, changed_fields):
        self._publish(
            EventTypes.ALARM_RULE_CHANGED,
            {
                "rule_id": rule.pk,
                "action": action,
                "changed_fields": sorted(changed_fields),
                "enabled": rule.enabled,
                "severity": rule.severity,
            },
            key=f"rule:{rule.pk}",
        )

    def _publish(self, event_type, payload, key=None):
        self._publisher.publish(Topics.database_events(), Event(type=event_type, payload=payload, source=self.SOURCE), key=key)
