from django.db import models

from .alarm_rule import AlarmRule
from .zone import Zone


class AlarmRuleState(models.Model):
    """État d'évaluation d'une règle pour une zone.

    Permet d'appliquer la durée minimale (état « en attente ») et d'éviter
    de recréer une alerte à chaque mesure tant que la situation persiste.
    """

    class Status(models.TextChoices):
        NORMAL = "normal", "Normal"
        PENDING = "pending", "En attente de la durée minimale"
        ACTIVE = "active", "En alarme"

    rule = models.ForeignKey(AlarmRule, on_delete=models.CASCADE, related_name="states")
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="alarm_states")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NORMAL)
    pending_since = models.DateTimeField(null=True, blank=True)
    last_value = models.FloatField(null=True, blank=True)
    last_observed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["rule", "zone"], name="unique_alarm_state_per_rule_zone"),
        ]

    def __str__(self):
        return f"{self.rule} / {self.zone.code}: {self.status}"
