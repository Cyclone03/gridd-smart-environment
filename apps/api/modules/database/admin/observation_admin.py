from django.contrib import admin

from modules.database.models import Observation


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
        "event_id",
    )
