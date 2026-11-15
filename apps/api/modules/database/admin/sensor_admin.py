from django.contrib import admin

from modules.database.models import Sensor

from .zones_changed_admin_mixin import ZonesChangedAdminMixin


@admin.register(Sensor)
class SensorAdmin(ZonesChangedAdminMixin, admin.ModelAdmin):
    list_display = ("node_id", "sensor_type", "zone", "unit", "active")
    list_filter = ("sensor_type", "zone", "active")
    search_fields = ("node_id", "label", "zone__name")
    readonly_fields = ("metadata",)
