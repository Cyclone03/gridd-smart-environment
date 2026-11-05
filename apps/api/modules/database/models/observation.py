from django.db import models
from django.utils import timezone

from .sensor import Sensor
from .zone import Zone


class Observation(models.Model):
    class QualityStatus(models.TextChoices):
        NORMAL = "normal", "Normal"
        SUSPICIOUS = "suspicious", "Suspecte"
        INVALID = "invalid", "Invalide"

    sensor = models.ForeignKey(Sensor, on_delete=models.PROTECT, related_name="observations")
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name="observations")
    type = models.CharField(max_length=30)
    value = models.FloatField()
    unit = models.CharField(max_length=20)
    observed_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)
    quality_status = models.CharField(max_length=20, choices=QualityStatus.choices, default=QualityStatus.NORMAL)
    quality_reason = models.CharField(max_length=255, blank=True)
    # Identifiant de l'événement d'ingestion : rend la persistance idempotente
    # lorsqu'un message Kafka est relivré. Vide pour les mesures antérieures.
    event_id = models.UUIDField(null=True, blank=True, unique=True, editable=False)

    class Meta:
        ordering = ["-observed_at", "-received_at"]
        indexes = [
            models.Index(fields=["zone", "type", "-observed_at"]),
            models.Index(fields=["sensor", "-observed_at"]),
        ]

    def __str__(self):
        return f"{self.zone.code} {self.type}: {self.value} {self.unit}"
