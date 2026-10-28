from django.conf import settings
from django.db import models
from django.utils import timezone

from . import metrics


class Zone(models.Model):
    class ZoneType(models.TextChoices):
        SERVER_ROOM = "server_room", "Salle serveur"
        MEETING_ROOM = "meeting_room", "Salle de réunion"
        OFFICE = "office", "Bureau"
        CUBICLE = "cubicle", "Cubicule"
        OPEN_WORKSPACE = "open_workspace", "Espace de travail ouvert"
        CLASSROOM = "classroom", "Salle de cours"
        LAB = "lab", "Laboratoire"
        OTHER = "other", "Autre"

    name = models.CharField(max_length=120)

    code = models.SlugField(
        max_length=80,
        unique=True,
    )

    zone_type = models.CharField(
        max_length=30,
        choices=ZoneType.choices,
        default=ZoneType.OTHER,
    )

    description = models.TextField(
        blank=True,
    )

    active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return self.name


class ThresholdProfile(models.Model):
    """Réglages du contrôle de qualité des données d'une zone.

    Les seuils d'alarme (température, humidité, son…) ne sont plus stockés
    ici : ils sont définis par des ``AlarmRule`` configurables depuis
    l'interface (voir docs/alarms.md). Ce profil ne porte plus que les
    paramètres de détection des données suspectes.
    """

    zone = models.OneToOneField(
        Zone,
        on_delete=models.CASCADE,
        related_name="threshold_profile",
    )

    # Active la détection des variations trop rapides pour cette zone.
    enabled = models.BooleanField(
        default=True,
    )

    max_temperature_delta_per_minute = models.FloatField(
        default=1,
    )

    max_humidity_delta_per_minute = models.FloatField(
        default=5,
    )

    max_co2_delta_per_minute = models.FloatField(
        default=800,
    )

    stuck_after_minutes = models.PositiveIntegerField(
        default=15,
    )

    max_sound_delta_per_minute = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Profil — {self.zone.name}"


class Sensor(models.Model):
    class SensorType(models.TextChoices):
        TEMPERATURE = "temperature", "Température"
        HUMIDITY = "humidity", "Humidité"
        CO2 = "co2", "CO₂"
        SOUND = "sound_level", "Niveau sonore"
        OCCUPANCY = "occupancy", "Occupation"

    node_id = models.CharField(
        max_length=150,
    )

    label = models.CharField(
        max_length=150,
        blank=True,
    )

    sensor_type = models.CharField(
        max_length=30,
        choices=SensorType.choices,
    )

    zone = models.ForeignKey(
        Zone,
        on_delete=models.PROTECT,
        related_name="sensors",
    )

    unit = models.CharField(
        max_length=20,
    )

    active = models.BooleanField(
        default=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "node_id",
                    "sensor_type",
                ],
                name="unique_node_measurement_type",
            )
        ]

        indexes = [
            models.Index(
                fields=[
                    "node_id",
                    "sensor_type",
                ]
            ),
            models.Index(
                fields=[
                    "zone",
                    "sensor_type",
                ]
            ),
        ]

    def __str__(self):
        return f"{self.node_id} ({self.sensor_type})"


class Observation(models.Model):
    class QualityStatus(models.TextChoices):
        NORMAL = "normal", "Normal"
        SUSPICIOUS = "suspicious", "Suspecte"
        INVALID = "invalid", "Invalide"

    sensor = models.ForeignKey(
        Sensor,
        on_delete=models.PROTECT,
        related_name="observations",
    )

    zone = models.ForeignKey(
        Zone,
        on_delete=models.PROTECT,
        related_name="observations",
    )

    type = models.CharField(
        max_length=30,
    )

    value = models.FloatField()

    unit = models.CharField(
        max_length=20,
    )

    observed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    received_at = models.DateTimeField(
        default=timezone.now,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    quality_status = models.CharField(
        max_length=20,
        choices=QualityStatus.choices,
        default=QualityStatus.NORMAL,
    )

    quality_reason = models.CharField(
        max_length=255,
        blank=True,
    )

    class Meta:
        ordering = [
            "-observed_at",
            "-received_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "zone",
                    "type",
                    "-observed_at",
                ]
            ),
            models.Index(
                fields=[
                    "sensor",
                    "-observed_at",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"{self.zone.code} "
            f"{self.type}: "
            f"{self.value} {self.unit}"
        )


class Alert(models.Model):
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

    zone = models.ForeignKey(
        Zone,
        on_delete=models.PROTECT,
        related_name="alerts",
    )

    observation = models.ForeignKey(
        Observation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
    )

    code = models.CharField(
        max_length=80,
    )

    message = models.CharField(
        max_length=255,
    )

    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
    )

    created_at = models.DateTimeField(
        default=timezone.now,
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    active = models.BooleanField(
        default=True,
    )

    # --- Traçabilité des alarmes issues des règles configurables ---------
    # Une ligne ``Alert`` représente un épisode complet : déclenchement
    # (created_at, trigger_value) puis retour à la normale (resolved_at,
    # resolution). Les alertes de qualité des données n'ont pas de règle.
    rule = models.ForeignKey(
        "AlarmRule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
    )

    trigger_value = models.FloatField(
        null=True,
        blank=True,
    )

    resolution = models.CharField(
        max_length=30,
        choices=Resolution.choices,
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["active", "-created_at"]),
            models.Index(fields=["rule", "zone", "active"]),
        ]

    def __str__(self):
        return f"{self.zone.code} - {self.code}"


class AlarmRule(models.Model):
    """Condition de déclenchement d'alarme définie depuis l'interface.

    Une règle s'applique à un type de mesure, soit pour une zone précise,
    soit pour toutes les zones (``zone`` nul). Elle est évaluée côté backend
    à chaque nouvelle observation (voir ``core.alarm_engine``).
    """

    class Operator(models.TextChoices):
        GT = metrics.OPERATOR_GT, "Supérieur à"
        GTE = metrics.OPERATOR_GTE, "Supérieur ou égal à"
        LT = metrics.OPERATOR_LT, "Inférieur à"
        LTE = metrics.OPERATOR_LTE, "Inférieur ou égal à"
        OUTSIDE_RANGE = metrics.OPERATOR_OUTSIDE_RANGE, "En dehors de l'intervalle"
        INSIDE_RANGE = metrics.OPERATOR_INSIDE_RANGE, "À l'intérieur de l'intervalle"

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

    metric = models.CharField(
        max_length=30,
        choices=Sensor.SensorType.choices,
    )

    operator = models.CharField(
        max_length=20,
        choices=Operator.choices,
    )

    # Seuil unique, ou borne basse pour les opérateurs d'intervalle.
    threshold = models.FloatField()

    # Borne haute, uniquement pour les opérateurs d'intervalle.
    threshold_high = models.FloatField(null=True, blank=True)

    enabled = models.BooleanField(default=True)

    severity = models.CharField(
        max_length=20,
        choices=Alert.Severity.choices,
        default=Alert.Severity.WARNING,
    )

    # Durée pendant laquelle la condition doit rester vraie avant de
    # déclencher l'alarme (0 = immédiat).
    min_duration_seconds = models.PositiveIntegerField(default=0)

    # Marge de retour à la normale : une alarme « > 30 » avec une
    # hystérésis de 1 ne se résout qu'à 29 ou moins.
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
        indexes = [
            models.Index(fields=["metric", "enabled"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(hysteresis__gte=0),
                name="alarm_rule_hysteresis_positive",
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(operator__in=sorted(metrics.RANGE_OPERATORS))
                    | models.Q(
                        threshold_high__isnull=False,
                        threshold_high__gt=models.F("threshold"),
                    )
                ),
                name="alarm_rule_range_bounds",
            ),
        ]

    @property
    def unit(self):
        definition = metrics.get_metric(self.metric)
        return definition.unit if definition else ""

    @property
    def alert_code(self):
        return f"RULE_{self.pk}"

    def __str__(self):
        return self.name


class AlarmRuleState(models.Model):
    """État d'évaluation d'une règle pour une zone donnée.

    Permet d'appliquer la durée minimale (état « en attente ») et d'éviter
    de recréer une alerte à chaque mesure tant que la situation persiste.
    """

    class Status(models.TextChoices):
        NORMAL = "normal", "Normal"
        PENDING = "pending", "En attente de la durée minimale"
        ACTIVE = "active", "En alarme"

    rule = models.ForeignKey(
        AlarmRule,
        on_delete=models.CASCADE,
        related_name="states",
    )
    zone = models.ForeignKey(
        Zone,
        on_delete=models.CASCADE,
        related_name="alarm_states",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NORMAL,
    )
    pending_since = models.DateTimeField(null=True, blank=True)
    last_value = models.FloatField(null=True, blank=True)
    last_observed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["rule", "zone"],
                name="unique_alarm_state_per_rule_zone",
            ),
        ]

    def __str__(self):
        return f"{self.rule} / {self.zone.code}: {self.status}"
