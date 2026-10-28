from django.contrib import admin

from .models import (
    AlarmRule,
    AlarmRuleState,
    Alert,
    Observation,
    Sensor,
    ThresholdProfile,
    Zone,
)


class ThresholdProfileInline(admin.StackedInline):
    """Paramètres de qualité des données. Les seuils d'alarme se gèrent
    désormais avec les règles d'alarme (interface GRIDD ou admin ci-dessous)."""

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


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "zone_type", "active")
    list_filter = ("zone_type", "active")
    search_fields = ("name", "code")
    inlines = [ThresholdProfileInline]


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ("node_id", "sensor_type", "zone", "unit", "active")
    list_filter = ("sensor_type", "zone", "active")
    search_fields = ("node_id", "label", "zone__name")
    readonly_fields = ("metadata",)


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = ("zone", "sensor", "type", "value", "unit", "quality_status", "observed_at")
    list_filter = ("zone", "type", "quality_status")
    search_fields = ("sensor__node_id", "zone__name")
    readonly_fields = (
        "sensor",
        "zone",
        "type",
        "value",
        "unit",
        "observed_at",
        "received_at",
        "metadata",
        "quality_status",
        "quality_reason",
    )


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("zone", "code", "rule", "severity", "active", "created_at", "resolved_at")
    list_filter = ("zone", "severity", "active", "resolution")
    search_fields = ("code", "message", "zone__name", "rule__name")
    readonly_fields = ("rule", "trigger_value", "resolution", "observation")


@admin.register(ThresholdProfile)
class ThresholdProfileAdmin(admin.ModelAdmin):
    list_display = (
        "zone",
        "enabled",
        "max_temperature_delta_per_minute",
        "max_humidity_delta_per_minute",
        "stuck_after_minutes",
    )
    list_filter = ("enabled", "zone")


@admin.register(AlarmRule)
class AlarmRuleAdmin(admin.ModelAdmin):
    # Les modifications faites ici ne passent pas par l'API : elles ne
    # résolvent pas automatiquement les alertes en cours. Préférer l'interface.
    list_display = (
        "name",
        "metric",
        "operator",
        "threshold",
        "threshold_high",
        "zone",
        "severity",
        "enabled",
        "updated_at",
    )
    list_filter = ("enabled", "metric", "severity", "zone")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(AlarmRuleState)
class AlarmRuleStateAdmin(admin.ModelAdmin):
    list_display = ("rule", "zone", "status", "pending_since", "last_value", "last_observed_at")
    list_filter = ("status", "zone")
    readonly_fields = (
        "rule",
        "zone",
        "status",
        "pending_since",
        "last_value",
        "last_observed_at",
        "updated_at",
    )
