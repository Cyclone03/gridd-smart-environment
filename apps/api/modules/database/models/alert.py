from django.db import models
from django.utils import timezone

from .observation import Observation
from .zone import Zone


class Alert(models.Model):
    """Un épisode d'alerte : déclenchement puis retour à la normale.

    ``code`` identifie l'origine : ``RULE_<id>`` pour une règle d'alarme,
    ``DATA_QUALITY_<MESURE>`` pour le contrôle de qualité des données.
    """

    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Attention"
        CRITICAL = "critical", "Critique"

    class Resolution(models.TextChoices):
        RETURNED_TO_NORMAL = "returned_to_normal", "Retour à la normale"
        RULE_DISABLED = "rule_disabled", "Règle désactivée"
        RULE_UPDATED = "rule_updated", "Règle modifiée"
        RULE_DELETED = "rule_deleted", "Règle supprimée"
        MIGRATED = "migrated", "Remplacée par les règles configurables"

    zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name="alerts")
    observation = models.ForeignKey(
        Observation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
    )
    code = models.CharField(max_length=80)
    message = models.CharField(max_length=255)
    severity = models.CharField(max_length=20, choices=Severity.choices)
    created_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)
    rule = models.ForeignKey(
        "AlarmRule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
    )
    trigger_value = models.FloatField(null=True, blank=True)
    resolution = models.CharField(max_length=30, choices=Resolution.choices, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["active", "-created_at"]),
            models.Index(fields=["rule", "zone", "active"]),
        ]

    def __str__(self):
        return f"{self.zone.code} - {self.code}"
