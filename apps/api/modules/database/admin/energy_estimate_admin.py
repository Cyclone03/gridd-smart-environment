from django.contrib import admin

from modules.database.models import EnergyEstimate


@admin.register(EnergyEstimate)
class EnergyEstimateAdmin(admin.ModelAdmin):
    list_display = ("zone", "start", "end", "occupancy", "total_wh", "hvac_estimated")
    readonly_fields = [field.name for field in EnergyEstimate._meta.fields]
    list_filter = ("zone",)
