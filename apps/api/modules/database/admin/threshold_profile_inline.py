from django.contrib import admin

from modules.database.models import ThresholdProfile


class ThresholdProfileInline(admin.StackedInline):
    """Paramètres de qualité des données. Les seuils d'alarme se gèrent avec
    les règles d'alarme (interface GRIDD ou admin des règles)."""

    model = ThresholdProfile
    extra = 0
    fieldsets = (
        ("Activation", {"fields": ("enabled",)}),
        (
            "Détection des variations rapides",
            {
                "fields": (
                    "max_temperature_delta_per_minute",
                    "max_humidity_delta_per_minute",
                    "max_sound_delta_per_minute",
                )
            },
        ),
        ("Capteur bloqué", {"fields": ("stuck_after_minutes",)}),
    )
