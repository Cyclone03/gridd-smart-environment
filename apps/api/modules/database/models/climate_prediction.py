from django.db import models

from .zone import Zone


class ClimatePrediction(models.Model):
    class PredictionMode(models.TextChoices):
        EXPERIMENTAL = "experimental", "Expérimental"
        OPERATIONAL = "operational", "Opérationnel"

    event_id = models.UUIDField(unique=True, editable=False)
    zone = models.ForeignKey(
        Zone,
        on_delete=models.PROTECT,
        related_name="climate_predictions",
    )
    generated_at = models.DateTimeField()
    target_at = models.DateTimeField()
    predicted_temperature_c = models.FloatField()
    predicted_humidity_percent = models.FloatField()
    model_version = models.CharField(max_length=255)
    prediction_mode = models.CharField(max_length=20, choices=PredictionMode.choices)

    class Meta:
        indexes = [models.Index(fields=["zone", "-target_at"])]
        ordering = ["-target_at"]

    def __str__(self):
        return f"{self.zone.code} prediction for {self.target_at.isoformat()}"
