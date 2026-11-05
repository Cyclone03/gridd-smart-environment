from shared.contracts.event_types import EventTypes
from shared.contracts.topics import Topics
from shared.messaging import Event


class AlarmEventsProducer:
    """Publie les décisions du moteur d'alarmes dans son topic de sortie.

    Clé de partition : la zone (événements d'une zone traités dans l'ordre)
    ou la règle pour les événements qui concernent toutes les zones.
    """

    SOURCE = "alarms"

    def __init__(self, publisher):
        self._publisher = publisher

    def alert_raised(self, *, zone_code, code, rule_id, severity, message, trigger_value, observation_id, refresh_fields):
        self._publish(
            EventTypes.ALERT_RAISED,
            {
                "zone_code": zone_code,
                "code": code,
                "rule_id": rule_id,
                "severity": severity,
                "message": message,
                "trigger_value": trigger_value,
                "observation_id": observation_id,
                "refresh_fields": list(refresh_fields),
            },
            key=zone_code,
        )

    def alert_resolved(self, *, zone_code, code, resolution, observation_id=None):
        self._publish(
            EventTypes.ALERT_RESOLVED,
            {"zone_code": zone_code, "code": code, "resolution": resolution, "observation_id": observation_id},
            key=zone_code,
        )

    def state_saved(self, *, rule_id, zone_code, state):
        self._publish(
            EventTypes.ALARM_STATE_SAVED,
            {
                "rule_id": rule_id,
                "zone_code": zone_code,
                "status": state.status,
                "pending_since": state.pending_since.isoformat() if state.pending_since else None,
                "last_value": state.last_value,
                "last_observed_at": state.last_observed_at.isoformat() if state.last_observed_at else None,
            },
            key=zone_code,
        )

    def rule_reset(self, *, rule_id, alert_code, resolution):
        self._publish(
            EventTypes.ALARM_RULE_RESET,
            {"rule_id": rule_id, "alert_code": alert_code, "resolution": resolution},
            key=f"rule:{rule_id}",
        )

    def severity_propagated(self, *, rule_id, alert_code, severity):
        self._publish(
            EventTypes.ALARM_RULE_SEVERITY_PROPAGATED,
            {"rule_id": rule_id, "alert_code": alert_code, "severity": severity},
            key=f"rule:{rule_id}",
        )

    def _publish(self, event_type, payload, key):
        self._publisher.publish(Topics.alarms_events(), Event(type=event_type, payload=payload, source=self.SOURCE), key=key)
