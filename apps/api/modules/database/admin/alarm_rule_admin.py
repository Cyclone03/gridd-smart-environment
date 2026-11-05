from django.contrib import admin

from modules.database.models import AlarmRule


@admin.register(AlarmRule)
class AlarmRuleAdmin(admin.ModelAdmin):
    # Les modifications faites ici ne passent pas par Kafka : elles ne
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
