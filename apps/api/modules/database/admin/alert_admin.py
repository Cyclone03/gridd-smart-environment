from django.contrib import admin

from modules.database.models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("zone", "code", "rule", "severity", "active", "created_at", "resolved_at")
    list_filter = ("zone", "severity", "active", "resolution")
    search_fields = ("code", "message", "zone__name", "rule__name")
    readonly_fields = ("rule", "trigger_value", "resolution", "observation")
