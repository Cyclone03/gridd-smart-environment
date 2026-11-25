from django.db import models


class WeatherSnapshot(models.Model):
    event_id = models.UUIDField(unique=True, editable=False)
    generated_at = models.DateTimeField()
    provider = models.CharField(max_length=32)
    current_at = models.DateTimeField()
    current_temperature_c = models.FloatField()
    current_relative_humidity_percent = models.FloatField()
    forecast_h1_at = models.DateTimeField()
    forecast_h1_temperature_c = models.FloatField()
    forecast_h1_relative_humidity_percent = models.FloatField()

    class Meta:
        ordering = ["-generated_at", "-pk"]

    def __str__(self):
        return f"{self.provider} weather snapshot at {self.generated_at.isoformat()}"
