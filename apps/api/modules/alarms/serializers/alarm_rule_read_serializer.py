from rest_framework import serializers

from modules.alarms.domain.condition_formatter import ConditionFormatter
from modules.database.models import AlarmRule


class AlarmRuleReadSerializer(serializers.ModelSerializer):
    """Représentation d'une règle d'alarme renvoyée par l'API."""

    zone = serializers.SlugRelatedField(slug_field="code", read_only=True)
    zone_name = serializers.CharField(source="zone.name", read_only=True, default=None)
    unit = serializers.CharField(read_only=True)
    condition_label = serializers.SerializerMethodField()
    active_alerts = serializers.IntegerField(read_only=True, default=0)
    created_by = serializers.CharField(source="created_by.get_username", read_only=True, default=None)
    updated_by = serializers.CharField(source="updated_by.get_username", read_only=True, default=None)

    class Meta:
        model = AlarmRule
        fields = [
            "id",
            "name",
            "description",
            "zone",
            "zone_name",
            "metric",
            "operator",
            "threshold",
            "threshold_high",
            "unit",
            "condition_label",
            "enabled",
            "severity",
            "min_duration_seconds",
            "hysteresis",
            "active_alerts",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]
        read_only_fields = fields

    def get_condition_label(self, rule):
        return ConditionFormatter.describe_rule(rule.metric, rule.operator, rule.threshold, rule.threshold_high)
