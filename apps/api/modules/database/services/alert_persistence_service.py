from django.db import transaction


class AlertPersistenceService:
    """Applique les événements du module ``alarms`` : alertes et états des règles.

    Publie ``alerts.changed`` dès que la liste des alertes actives a changé.
    """

    def __init__(self, *, zone_writer, alert_writer, state_writer, producer):
        self._zone_writer = zone_writer
        self._alert_writer = alert_writer
        self._state_writer = state_writer
        self._producer = producer

    def raise_alert(self, payload):
        with transaction.atomic():
            zone = self._zone(payload)
            changed = zone is not None and self._alert_writer.raise_alert(
                zone=zone,
                code=payload["code"],
                rule_id=payload.get("rule_id"),
                severity=payload["severity"],
                message=payload["message"],
                trigger_value=payload.get("trigger_value"),
                observation_id=payload.get("observation_id"),
                refresh_fields=payload.get("refresh_fields") or [],
            )
        self._notify(changed, payload["zone_code"])

    def resolve_alert(self, payload):
        with transaction.atomic():
            zone = self._zone(payload)
            changed = zone is not None and self._alert_writer.resolve(
                zone=zone,
                code=payload["code"],
                resolution=payload["resolution"],
                observation_id=payload.get("observation_id"),
            )
        self._notify(changed, payload["zone_code"])

    def reset_rule(self, payload):
        with transaction.atomic():
            closed = self._alert_writer.resolve_code(code=payload["alert_code"], resolution=payload["resolution"])
            self._state_writer.reset_rule(payload["rule_id"])
        self._notify(closed > 0)

    def propagate_severity(self, payload):
        with transaction.atomic():
            updated = self._alert_writer.change_severity(code=payload["alert_code"], severity=payload["severity"])
        self._notify(updated > 0)

    def save_state(self, payload):
        with transaction.atomic():
            zone = self._zone(payload)
            if zone is not None:
                self._state_writer.save(
                    rule_id=payload["rule_id"],
                    zone=zone,
                    status=payload["status"],
                    pending_since=payload.get("pending_since"),
                    last_value=payload.get("last_value"),
                    last_observed_at=payload.get("last_observed_at"),
                )

    def _zone(self, payload):
        return self._zone_writer.find(payload["zone_code"])

    def _notify(self, changed, zone_code=None):
        if changed:
            self._producer.alerts_changed(zone_code)
