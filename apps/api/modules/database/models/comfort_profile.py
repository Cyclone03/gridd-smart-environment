from django.db import models

from .zone import Zone


class ComfortProfile(models.Model):
    """Ancien profil conservé pour préserver les données déjà enregistrées."""

    zone = models.OneToOneField(Zone, on_delete=models.CASCADE, related_name="comfort_profile")
    temperature_min = models.FloatField()
    temperature_max = models.FloatField()
    temperature_tolerance = models.FloatField()
    humidity_min = models.FloatField()
    humidity_max = models.FloatField()
    humidity_tolerance = models.FloatField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Confort — {self.zone.name}"
