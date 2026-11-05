from django.db import models

from .zone import Zone


class Sensor(models.Model):
    class SensorType(models.TextChoices):
        TEMPERATURE = "temperature", "Température"
        HUMIDITY = "humidity", "Humidité"
        CO2 = "co2", "CO₂"
        SOUND = "sound_level", "Niveau sonore"
        OCCUPANCY = "occupancy", "Occupation"

    node_id = models.CharField(max_length=150)
    label = models.CharField(max_length=150, blank=True)
    sensor_type = models.CharField(max_length=30, choices=SensorType.choices)
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name="sensors")
    unit = models.CharField(max_length=20)
    active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["node_id", "sensor_type"], name="unique_node_measurement_type"),
        ]
        indexes = [
            models.Index(fields=["node_id", "sensor_type"]),
            models.Index(fields=["zone", "sensor_type"]),
        ]

    def __str__(self):
        return f"{self.node_id} ({self.sensor_type})"
