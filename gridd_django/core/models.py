from django.db import models
from django.utils import timezone


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
    zone = models.OneToOneField(
        Zone,
        on_delete=models.CASCADE,
        related_name="threshold_profile",
    )

    # Tant que disabled, pas d'alertes automatiques.
    enabled = models.BooleanField(
        default=False,
    )

    temperature_min = models.FloatField(
        default=20,
    )

    temperature_max = models.FloatField(
        default=25,
    )

    humidity_min = models.FloatField(
        default=30,
    )

    humidity_max = models.FloatField(
        default=60,
    )

    co2_warning = models.FloatField(
        default=800,
    )

    co2_critical = models.FloatField(
        default=1200,
    )

    sound_warning = models.FloatField(
        default=55,
    )

    sound_critical = models.FloatField(
        default=70,
    )

    max_temperature_delta_per_minute = models.FloatField(
        default=5,
    )

    max_humidity_delta_per_minute = models.FloatField(
        default=20,
    )

    max_co2_delta_per_minute = models.FloatField(
        default=800,
    )

    max_sound_delta_per_minute = models.FloatField(
        default=40,
    )

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

    def __str__(self):
        return f"{self.zone.code} - {self.code}"