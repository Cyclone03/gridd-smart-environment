from modules.database.models import Alert


class AlertRepository:
    """Lecture des alertes (lecture seule)."""

    def search(self, *, zone=None, active=None, rule=None, severity=None, since=None, until=None):
        alerts = Alert.objects.select_related("zone", "observation", "rule")
        if zone:
            alerts = alerts.filter(zone__code=zone)
        if active is not None:
            alerts = alerts.filter(active=active)
        if rule is not None:
            alerts = alerts.filter(rule_id=rule)
        if severity:
            alerts = alerts.filter(severity=severity)
        if since:
            alerts = alerts.filter(created_at__gte=since)
        if until:
            alerts = alerts.filter(created_at__lte=until)
        return alerts

    def get(self, alert_id) -> Alert | None:
        try:
            return self.search().filter(pk=int(alert_id)).first()
        except (TypeError, ValueError):
            return None

    def is_active(self, zone_code, code) -> bool:
        return Alert.objects.filter(zone__code=zone_code, code=code, active=True).exists()
