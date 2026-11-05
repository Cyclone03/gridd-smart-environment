from django.contrib import admin

from modules.database.models import AlarmRuleState


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
