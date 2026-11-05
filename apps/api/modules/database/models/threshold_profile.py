from django.db import models

from .zone import Zone


class ThresholdProfile(models.Model):
    """Réglages du contrôle de qualité des données d'une zone.

    Les seuils d'alarme sont des ``AlarmRule`` (voir docs/alarms.md) ; ce
    profil ne porte que les paramètres de détection des données suspectes.
    """

    zone = models.OneToOneField(Zone, on_delete=models.CASCADE, related_name="threshold_profile")
    # Active la détection des variations trop rapides pour cette zone.
    enabled = models.BooleanField(default=True)
    max_temperature_delta_per_minute = models.FloatField(default=1)
    max_humidity_delta_per_minute = models.FloatField(default=5)
    max_co2_delta_per_minute = models.FloatField(default=800)
    stuck_after_minutes = models.PositiveIntegerField(default=15)
    max_sound_delta_per_minute = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Profil — {self.zone.name}"
