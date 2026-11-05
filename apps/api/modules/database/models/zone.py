from django.db import models


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
    code = models.SlugField(max_length=80, unique=True)
    zone_type = models.CharField(max_length=30, choices=ZoneType.choices, default=ZoneType.OTHER)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
