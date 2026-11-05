from django.db import models

from .zone import Zone


class EnergyProfile(models.Model):
    """Paramètres personnalisés du modèle d'estimation énergétique d'une zone.

    Sans enregistrement, le module ``energy`` applique les valeurs par défaut
    du type d'espace.
    """

    zone = models.OneToOneField(Zone, on_delete=models.CASCADE, related_name="energy_profile")
    floor_area_m2 = models.FloatField()
    lighting_w_per_m2 = models.FloatField()
    equipment_base_w = models.FloatField()
    equipment_w_per_person = models.FloatField()
    default_occupancy = models.PositiveIntegerField()
    envelope_ua_w_per_k = models.FloatField()
    ventilation_l_s_per_person = models.FloatField()
    outdoor_temperature_c = models.FloatField()
    heating_cop = models.FloatField()
    cooling_cop = models.FloatField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Énergie — {self.zone.name}"
