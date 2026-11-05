from django.db import models

from .observation import Observation
from .zone import Zone


class EnergyEstimate(models.Model):
    """Énergie estimée d'une zone sur un intervalle entre deux mesures."""

    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="energy_estimates")
    # Observation qui clôt l'intervalle : rend la persistance idempotente.
    observation = models.OneToOneField(
        Observation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="energy_estimate",
    )
    start = models.DateTimeField()
    end = models.DateTimeField()
    duration_seconds = models.FloatField()
    indoor_temperature = models.FloatField(null=True, blank=True)
    occupancy = models.FloatField()
    # "sensor" : capteur d'occupation ; "profile" : occupation par défaut de la zone.
    occupancy_source = models.CharField(max_length=10)
    hvac_estimated = models.BooleanField()
    lighting_wh = models.FloatField()
    equipment_wh = models.FloatField()
    heating_wh = models.FloatField()
    cooling_wh = models.FloatField()
    total_wh = models.FloatField()

    class Meta:
        indexes = [models.Index(fields=["zone", "end"]), models.Index(fields=["end"])]

    def __str__(self):
        return f"{self.zone.code} {self.end:%Y-%m-%d %H:%M} : {self.total_wh:.1f} Wh"
