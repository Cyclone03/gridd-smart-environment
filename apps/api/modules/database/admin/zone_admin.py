from django.contrib import admin

from modules.database.models import Zone

from .threshold_profile_inline import ThresholdProfileInline


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "zone_type", "active")
    list_filter = ("zone_type", "active")
    search_fields = ("name", "code")
    inlines = [ThresholdProfileInline]
