from django.db import models

from .observation import Observation
from .zone import Zone


class ComfortAssessment(models.Model):
    """Ancienne évaluation conservée pour préserver les données déjà enregistrées."""

    class Level(models.TextChoices):
        COMFORTABLE = "comfortable", "Confortable"
        ACCEPTABLE = "acceptable", "Acceptable"
        UNCOMFORTABLE = "uncomfortable", "Inconfortable"
        UNKNOWN = "unknown", "Indéterminé"

    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="comfort_assessments")
    # Observation à l'origine de l'évaluation : rend la persistance idempotente.
    observation = models.OneToOneField(
        Observation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comfort_assessment",
    )
    assessed_at = models.DateTimeField()
    temperature = models.FloatField(null=True, blank=True)
    humidity = models.FloatField(null=True, blank=True)
    temperature_status = models.CharField(max_length=20)
    humidity_status = models.CharField(max_length=20)
    level = models.CharField(max_length=20, choices=Level.choices)
    score = models.FloatField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["zone", "-assessed_at"])]

    def __str__(self):
        return f"{self.zone.code} {self.assessed_at:%Y-%m-%d %H:%M} : {self.level}"
