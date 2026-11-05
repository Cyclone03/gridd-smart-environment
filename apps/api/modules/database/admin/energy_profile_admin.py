from django.contrib import admin

from modules.database.models import EnergyProfile


@admin.register(EnergyProfile)
class EnergyProfileAdmin(admin.ModelAdmin):
    list_display = ("zone", "floor_area_m2", "equipment_base_w", "default_occupancy", "outdoor_temperature_c", "updated_at")
