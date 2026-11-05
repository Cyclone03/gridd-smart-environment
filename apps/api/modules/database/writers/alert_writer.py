from django.utils import timezone

from modules.database.models import AlarmRule, Alert


class AlertWriter:
    """Ouverture, mise à jour et clôture des épisodes d'alerte.

    Une seule alerte active par (zone, code). Chaque méthode retourne vrai si
    la liste des alertes actives a changé (création, clôture, gravité), ce qui
    déclenche la notification des tableaux de bord.
    """

    # Champs qu'un événement ``alert.raised`` peut rafraîchir sur l'alerte active.
    REFRESHABLE_FIELDS = {
        "observation": "observation_id",
        "message": "message",
        "severity": "severity",
        "trigger_value": "trigger_value",
    }

    def raise_alert(self, *, zone, code, rule_id, severity, message, trigger_value, observation_id, refresh_fields) -> bool:
        if rule_id is not None and not AlarmRule.objects.filter(pk=rule_id).exists():
            return False  # règle supprimée entre-temps

        values = {
            "observation_id": observation_id,
            "message": message[:255],
            "severity": severity,
            "trigger_value": trigger_value,
        }
        active = Alert.objects.filter(zone=zone, code=code, active=True).first()
        if active is not None:
            columns = [self.REFRESHABLE_FIELDS[field] for field in refresh_fields if field in self.REFRESHABLE_FIELDS]
            for column in columns:
                setattr(active, column, values[column])
            if columns:
                active.save(update_fields=columns)
            return False

        Alert.objects.create(zone=zone, code=code, rule_id=rule_id, **values)
        return True

    def resolve(self, *, zone, code, resolution, observation_id=None) -> bool:
        active = Alert.objects.filter(zone=zone, code=code, active=True).first()
        if active is None:
            return False
        active.active = False
        active.resolved_at = timezone.now()
        active.resolution = resolution
        update_fields = ["active", "resolved_at", "resolution"]
        if observation_id is not None:
            active.observation_id = observation_id
            update_fields.append("observation")
        active.save(update_fields=update_fields)
        return True

    def resolve_code(self, *, code, resolution) -> int:
        """Clôt toutes les alertes actives d'un code (toutes zones)."""
        return Alert.objects.filter(code=code, active=True).update(
            active=False,
            resolved_at=timezone.now(),
            resolution=resolution,
        )

    def change_severity(self, *, code, severity) -> int:
        return Alert.objects.filter(code=code, active=True).update(severity=severity)
