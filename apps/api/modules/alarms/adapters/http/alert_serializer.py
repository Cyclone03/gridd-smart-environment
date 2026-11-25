from rest_framework import serializers

from modules.database.models import Alert


class AlertSerializer(serializers.ModelSerializer):
    zone_code = serializers.CharField(source="zone.code", read_only=True)
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    rule_name = serializers.CharField(source="rule.name", read_only=True, default=None)

    class Meta:
        model = Alert
        fields = [
            "id",
            "zone",
            "zone_code",
            "zone_name",
            "observation",
            "rule",
            "rule_name",
            "code",
            "message",
            "severity",
            "trigger_value",
            "created_at",
            "resolved_at",
            "resolution",
            "active",
        ]
        read_only_fields = fields
