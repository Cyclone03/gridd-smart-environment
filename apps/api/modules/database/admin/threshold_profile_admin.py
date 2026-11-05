from django.contrib import admin

from modules.database.models import ThresholdProfile


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
