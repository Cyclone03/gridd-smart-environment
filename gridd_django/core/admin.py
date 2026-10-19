from django.contrib import admin

from .models import (
    Alert,
    Observation,
    Sensor,
    ThresholdProfile,
    Zone,
)


class ThresholdProfileInline(admin.StackedInline):
    model = ThresholdProfile
    extra = 0

    fieldsets = (
        (
            "Activation",
            {
                "fields": (
                    "enabled",
                )
            },
        ),
        (
            "Température",
            {
                "fields": (
                    "temperature_min",
                    "temperature_max",
                    "max_temperature_delta_per_minute",
                )
            },
        ),
        (
            "Humidité",
            {
                "fields": (
                    "humidity_min",
                    "humidity_max",
                    "max_humidity_delta_per_minute",
                )
            },
        ),
        (
            "CO₂",
            {
                "fields": (
                    "co2_warning",
                    "co2_critical",
                    "max_co2_delta_per_minute",
                )
            },
        ),
        (
            "Acoustique",
            {
                "fields": (
                    "sound_warning",
                    "sound_critical",
                    "max_sound_delta_per_minute",
                )
            },
        ),
    )


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "zone_type",
        "active",
    )

    list_filter = (
        "zone_type",
        "active",
    )

    search_fields = (
        "name",
        "code",
    )

    inlines = [
        ThresholdProfileInline,
    ]


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = (
        "node_id",
        "sensor_type",
        "zone",
        "unit",
        "active",
    )

    list_filter = (
        "sensor_type",
        "zone",
        "active",
    )

    search_fields = (
        "node_id",
        "label",
        "zone__name",
    )

    readonly_fields = (
        "metadata",
    )


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = (
        "zone",
        "sensor",
        "type",
        "value",
        "unit",
        "quality_status",
        "observed_at",
    )

    list_filter = (
        "zone",
        "type",
        "quality_status",
    )

    search_fields = (
        "sensor__node_id",
        "zone__name",
    )

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
    list_display = (
        "zone",
        "code",
        "severity",
        "active",
        "created_at",
    )

    list_filter = (
        "zone",
        "severity",
        "active",
    )

    search_fields = (
        "code",
        "message",
        "zone__name",
    )


@admin.register(ThresholdProfile)
class ThresholdProfileAdmin(admin.ModelAdmin):
    list_display = (
        "zone",
        "enabled",
        "temperature_min",
        "temperature_max",
        "humidity_min",
        "humidity_max",
        "sound_warning",
        "sound_critical",
    )

    list_filter = (
        "enabled",
        "zone",
    )