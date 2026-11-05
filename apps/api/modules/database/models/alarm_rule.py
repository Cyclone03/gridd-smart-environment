from django.conf import settings
from django.db import models

from shared.metrics.metric_catalog import MetricCatalog
from shared.metrics.operator import Operator as Operators

from .alert import Alert
from .sensor import Sensor
from .zone import Zone


class AlarmRule(models.Model):
    """Condition de déclenchement d'alarme définie depuis l'interface.

    S'applique à un type de mesure, pour une zone précise ou pour toutes les
    zones (``zone`` nul). Évaluée par le module ``alarms`` à chaque mesure.
    """

    class Operator(models.TextChoices):
        GT = Operators.GT, "Supérieur à"
        GTE = Operators.GTE, "Supérieur ou égal à"
        LT = Operators.LT, "Inférieur à"
        LTE = Operators.LTE, "Inférieur ou égal à"
        OUTSIDE_RANGE = Operators.OUTSIDE_RANGE, "En dehors de l'intervalle"
        INSIDE_RANGE = Operators.INSIDE_RANGE, "À l'intérieur de l'intervalle"

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    zone = models.ForeignKey(
        Zone,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="alarm_rules",
        help_text="Vide : la règle s'applique à toutes les zones.",
    )
    metric = models.CharField(max_length=30, choices=Sensor.SensorType.choices)
    operator = models.CharField(max_length=20, choices=Operator.choices)
    # Seuil unique, ou borne basse pour les opérateurs d'intervalle.
    threshold = models.FloatField()
    # Borne haute, uniquement pour les opérateurs d'intervalle.
    threshold_high = models.FloatField(null=True, blank=True)
    enabled = models.BooleanField(default=True)
    severity = models.CharField(max_length=20, choices=Alert.Severity.choices, default=Alert.Severity.WARNING)
    # Durée pendant laquelle la condition doit rester vraie (0 = immédiat).
    min_duration_seconds = models.PositiveIntegerField(default=0)
    # Marge de retour à la normale : « > 30 » avec 1 se résout à 29 ou moins.
    hysteresis = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["metric", "name", "id"]
        indexes = [models.Index(fields=["metric", "enabled"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(hysteresis__gte=0), name="alarm_rule_hysteresis_positive"),
            models.CheckConstraint(
                condition=(
                    ~models.Q(operator__in=sorted(Operators.RANGE))
                    | models.Q(threshold_high__isnull=False, threshold_high__gt=models.F("threshold"))
                ),
                name="alarm_rule_range_bounds",
            ),
        ]

    @property
    def unit(self):
        definition = MetricCatalog.get(self.metric)
        return definition.unit if definition else ""

    @property
    def alert_code(self):
        return f"RULE_{self.pk}"

    def __str__(self):
        return self.name
